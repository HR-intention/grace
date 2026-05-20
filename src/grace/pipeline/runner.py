from __future__ import annotations

import asyncio
import json
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.prompt import build_prompt
from grace.pipeline.types import GenerationContext, GenerationResult


# A "sink" consumes one chunk of output text. Default sinks write to the
# process's stdout/stderr (so the user sees claude's progress live); tests
# substitute no-op sinks via the runner's constructor.
LineSink = Callable[[str], None]


def _stdout_sink(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def _stderr_sink(text: str) -> None:
    sys.stderr.write(text)
    sys.stderr.flush()


def _truncate(s: str, limit: int = 120) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def format_stream_event(raw_line: str) -> str | None:
    """Turn one JSONL event from `claude -p --output-format stream-json` into a
    human-readable progress line. Returns None to skip an event entirely.

    The event shape follows Anthropic's Messages API: `system`, `assistant`,
    `user`, `result`. Anything we don't recognise is passed through as raw
    (truncated) so unexpected events still surface rather than vanish.
    """
    stripped = raw_line.strip()
    if not stripped:
        return None
    try:
        event: Any = json.loads(stripped)
    except json.JSONDecodeError:
        # Not JSON — must be plain text (e.g., the claude CLI's own startup
        # banner). Pass it through verbatim.
        return raw_line

    if not isinstance(event, dict):
        return raw_line

    etype = event.get("type")

    # Noisy events that the user doesn't need to see (hook firings, rate-limit
    # heartbeats, raw usage stats). Skip them silently — they're useful for
    # post-mortem inspection (still kept in the raw buffer) but not for live
    # progress.
    if etype == "rate_limit_event":
        return None
    if etype == "system" and event.get("subtype", "").startswith("hook_"):
        return None

    if etype == "system" and event.get("subtype") == "init":
        model = event.get("model", "?")
        tools = event.get("tools") or []
        return f"[claude] session started (model={model}, {len(tools)} tools)\n"

    if etype == "assistant":
        message = event.get("message") or {}
        out_lines: list[str] = []
        for part in message.get("content") or []:
            ptype = part.get("type") if isinstance(part, dict) else None
            if ptype == "text":
                text = (part.get("text") or "").rstrip()
                if text:
                    out_lines.append(text)
            elif ptype == "tool_use":
                name = part.get("name", "?")
                inp = part.get("input") or {}
                hint = _tool_use_hint(name, inp)
                out_lines.append(f"[claude] → {name}({hint})")
        if not out_lines:
            return None
        return "\n".join(out_lines) + "\n"

    if etype == "user":
        message = event.get("message") or {}
        results: list[str] = []
        for part in message.get("content") or []:
            ptype = part.get("type") if isinstance(part, dict) else None
            if ptype == "tool_result":
                content = part.get("content")
                snippet = _result_snippet(content)
                tag = "✗" if part.get("is_error") else "←"
                results.append(f"[claude] {tag} {snippet}")
        if not results:
            return None
        return "\n".join(results) + "\n"

    if etype == "result":
        subtype = event.get("subtype", "?")
        cost = event.get("total_cost_usd")
        dur = event.get("duration_ms")
        bits = [f"subtype={subtype}"]
        if cost is not None:
            bits.append(f"cost=${cost:.4f}")
        if dur is not None:
            bits.append(f"duration={dur/1000:.1f}s")
        if event.get("is_error"):
            bits.append("ERROR")
        return f"[claude] ── done ({', '.join(bits)})\n"

    # Unknown event type — surface just the type so the user knows something
    # arrived without dumping a potentially-huge JSON payload.
    subtype = event.get("subtype")
    descriptor = f"{etype}/{subtype}" if subtype else str(etype)
    return f"[claude] ?? unknown event: {descriptor}\n"


def _tool_use_hint(name: str, inp: dict[str, Any]) -> str:
    """Compress a tool-use input dict into a one-line hint."""
    # Pick the field that's most informative per tool. Falls back to a
    # truncated JSON dump for unknown tools.
    if name in {"Read", "Write", "Edit"}:
        path = inp.get("file_path") or inp.get("path") or "?"
        if name == "Write" and "content" in inp:
            size = len(inp.get("content") or "")
            return f"{path}, {size}B"
        return str(path)
    if name == "Bash":
        return _truncate(str(inp.get("command", "?")), 100)
    if name == "Glob":
        return str(inp.get("pattern", "?"))
    if name == "Grep":
        pat = inp.get("pattern", "?")
        path = inp.get("path", "")
        return f"{pat}" + (f" in {path}" if path else "")
    if name == "TodoWrite":
        todos = inp.get("todos") or []
        return f"{len(todos)} item(s)"
    # Generic: keys-only summary keeps it short.
    return _truncate(",".join(sorted(inp.keys())), 60)


def _result_snippet(content: Any) -> str:
    """Render a tool_result body as a one-line summary."""
    if isinstance(content, str):
        if not content:
            return "(empty result)"
        size = len(content)
        return f"result ({size}B): {_truncate(content, 80)}"
    if isinstance(content, list):
        return f"result ({len(content)} parts)"
    return _truncate(json.dumps(content)[:200], 80)


async def _tee(
    stream: asyncio.StreamReader | None,
    buffer: list[str],
    sink: LineSink,
    formatter: Callable[[str], str | None] | None = None,
) -> None:
    """Drain `stream` line-by-line.

    Each raw chunk is appended to `buffer` (used later for error scanning and
    the GenerationResult transcript). The same chunk is then passed through
    `formatter` if provided; the formatter's return value (or the raw chunk
    if no formatter) is forwarded to `sink`. A formatter returning None means
    "swallow this event silently".

    Robust against oversized lines: if a single line exceeds the
    StreamReader's `limit`, readline raises ValueError. We surface a marker
    in the sink and continue — losing that one event is far better than
    aborting the whole stream and leaving the user staring at a traceback.
    """
    if stream is None:
        return
    while True:
        try:
            chunk = await stream.readline()
        except ValueError:
            # A single line was longer than the StreamReader's limit.
            # The reader has already discarded the offending line; we just
            # tell the user and move on so the rest of the run is still
            # visible.
            sink("[grace] (oversized stream event skipped — readline limit overrun)\n")
            continue
        if not chunk:
            return
        text = chunk.decode(errors="replace")
        buffer.append(text)
        formatted = formatter(text) if formatter is not None else text
        if formatted is not None:
            sink(formatted)


# Generous stdout limit for the claude subprocess. Real generations embed
# whole files (~80 KB+ markdown sources) in tool_result events as JSON-escaped
# strings — the default 64 KiB asyncio limit fires almost immediately. 64 MB
# is more than enough for any single conceivable event and costs nothing when
# unused.
_SUBPROCESS_LINE_LIMIT = 64 * 1024 * 1024


@dataclass(frozen=True)
class ClaudeCodeRunner:
    """Invokes the local Claude Code CLI to generate a connector package.

    There is exactly one AI backend. No abstraction. No registry. No fallback.

    By default, the subprocess's stdout/stderr are streamed live to the host
    process's stdout/stderr so the user sees claude's progress during long
    generations. Pass alternative sinks for quiet operation (tests / library use).
    """

    cli_path: Path | None = None
    timeout_s: float = 6000.0
    stdout_sink: LineSink = field(default=_stdout_sink)
    stderr_sink: LineSink = field(default=_stderr_sink)

    def _resolve_binary(self) -> Path:
        if self.cli_path is not None:
            if not self.cli_path.exists():
                raise GraceError(
                    reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND,
                    detail=f"configured cli_path does not exist: {self.cli_path}",
                )
            return self.cli_path
        found = shutil.which("claude")
        if found is None:
            raise GraceError(
                reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND,
                detail="`claude` binary not found in PATH; install Claude Code first",
            )
        return Path(found)

    async def is_available(self) -> tuple[bool, str]:
        """For `grace doctor`. Returns (healthy, detail)."""
        try:
            binary = self._resolve_binary()
        except GraceError as e:
            return (False, e.detail or e.reason.value)
        try:
            proc = await asyncio.create_subprocess_exec(
                str(binary),
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except (TimeoutError, asyncio.TimeoutError):
            return (False, "claude --version timed out")
        except OSError as e:
            return (False, f"failed to spawn claude: {e}")
        if proc.returncode != 0:
            return (
                False,
                (stderr or stdout).decode(errors="replace").strip() or "non-zero exit",
            )
        return (True, stdout.decode(errors="replace").strip())

    async def generate(self, context: GenerationContext) -> GenerationResult:
        """Spawn Claude Code in `context.output_dir` with the assembled prompt as stdin.

        Output streams live to `stdout_sink` / `stderr_sink` (default: the host
        process's own stdout/stderr) so the user has visibility into a
        potentially-long subprocess run.
        """
        binary = self._resolve_binary()
        prompt = build_prompt(context)
        context.output_dir.mkdir(parents=True, exist_ok=True)

        if context.psp_docs.source_kind == "url" and context.psp_docs.content_bytes is not None:
            cached = context.output_dir / "_psp_source_cache"
            cached.write_bytes(context.psp_docs.content_bytes)

        # `--output-format stream-json --verbose` makes claude emit one JSONL
        # event per tool call / message chunk, which we parse into live
        # progress lines via `format_stream_event`. Without these flags claude
        # only writes its final text at exit — minutes of silence for the user.
        # `limit` raises the StreamReader's per-line cap above the asyncio
        # default 64 KiB so tool_result events embedding whole markdown files
        # don't trip a readline ValueError.
        proc = await asyncio.create_subprocess_exec(
            str(binary),
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--output-format",
            "stream-json",
            "--verbose",
            cwd=str(context.output_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=_SUBPROCESS_LINE_LIMIT,
        )

        # Feed the prompt and close stdin so claude doesn't wait for more input.
        if proc.stdin is not None:
            proc.stdin.write(prompt.encode("utf-8"))
            try:
                await proc.stdin.drain()
            finally:
                proc.stdin.close()

        stdout_buf: list[str] = []
        stderr_buf: list[str] = []

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _tee(proc.stdout, stdout_buf, self.stdout_sink, format_stream_event),
                    _tee(proc.stderr, stderr_buf, self.stderr_sink),
                    proc.wait(),
                ),
                timeout=self.timeout_s,
            )
        except (TimeoutError, asyncio.TimeoutError) as e:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            raise GraceError(
                reason=GraceErrorReason.CLAUDE_CODE_TIMEOUT,
                detail=f"claude did not finish within {self.timeout_s}s",
            ) from e

        rc = proc.returncode or 0
        stdout_text = "".join(stdout_buf)
        stderr_text = "".join(stderr_buf)

        if rc != 0:
            # `claude -p` writes 401 auth failures to stdout, not stderr — scan both
            # streams + watch for the JSON `authentication_error` pattern.
            combined = (stderr_text + "\n" + stdout_text).lower()
            looks_like_auth = (
                "authentication_error" in combined
                or "401" in combined
                or "auth" in combined
                or "login" in combined
            )
            reason = (
                GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED
                if looks_like_auth
                else GraceErrorReason.CLAUDE_CODE_FAILED
            )
            raise GraceError(reason=reason, detail=stderr_text.strip() or stdout_text.strip())

        files = sorted(p for p in context.output_dir.rglob("*.py"))
        return GenerationResult(
            output_dir=context.output_dir,
            files_written=files,
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=rc,
        )
