from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.prompt import build_prompt
from grace.pipeline.types import GenerationContext, GenerationResult


@dataclass(frozen=True)
class ClaudeCodeRunner:
    """Invokes the local Claude Code CLI to generate a connector package.

    There is exactly one AI backend. No abstraction. No registry. No fallback.
    """

    cli_path: Path | None = None
    timeout_s: float = 1800.0

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
        """Spawn Claude Code in `context.output_dir` with the assembled prompt as stdin."""
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
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
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
        stderr_text = stderr.decode(errors="replace")
        stdout_text = stdout.decode(errors="replace")
        if rc != 0:
            reason = (
                GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED
                if "auth" in stderr_text.lower() or "login" in stderr_text.lower()
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
