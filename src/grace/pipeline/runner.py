from __future__ import annotations

import asyncio
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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


async def _tee(
    stream: asyncio.StreamReader | None,
    buffer: list[str],
    sink: LineSink,
) -> None:
    """Drain `stream` line-by-line; append each chunk to `buffer` and forward to `sink`.

    Used to give the user real-time progress on a long-running `claude -p`
    subprocess while still capturing the full transcript for error inspection.
    """
    if stream is None:
        return
    while True:
        chunk = await stream.readline()
        if not chunk:
            return
        text = chunk.decode(errors="replace")
        buffer.append(text)
        sink(text)


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

        proc = await asyncio.create_subprocess_exec(
            str(binary),
            "-p",
            "--permission-mode",
            "acceptEdits",
            cwd=str(context.output_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
                    _tee(proc.stdout, stdout_buf, self.stdout_sink),
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
