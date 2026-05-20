from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.runner import ClaudeCodeRunner
from grace.pipeline.types import GenerationContext, PspDocs


# --- test fakes ---------------------------------------------------------------


class _AsyncBytesReader:
    """Minimal async stream reader: yields the given bytes line-by-line then EOF."""

    def __init__(self, data: bytes):
        self._lines = data.splitlines(keepends=True) or []
        self._idx = 0

    async def readline(self) -> bytes:
        if self._idx >= len(self._lines):
            return b""
        line = self._lines[self._idx]
        self._idx += 1
        return line


class _AsyncWritable:
    """Minimal stdin stub matching the asyncio.StreamWriter interface we use."""

    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FakeProc:
    """Subprocess stub matching the surface ClaudeCodeRunner.generate uses:
    stdin/stdout/stderr async streams + an async wait() + a kill()."""

    def __init__(
        self,
        *,
        stdout_bytes: bytes = b"",
        stderr_bytes: bytes = b"",
        returncode: int = 0,
        wait_raises: type[BaseException] | None = None,
    ):
        self.stdin = _AsyncWritable()
        self.stdout = _AsyncBytesReader(stdout_bytes)
        self.stderr = _AsyncBytesReader(stderr_bytes)
        self._returncode = returncode
        self._wait_raises = wait_raises

    @property
    def returncode(self) -> int | None:
        return self._returncode

    async def wait(self) -> int:
        if self._wait_raises is not None:
            raise self._wait_raises("simulated")
        return self._returncode

    def kill(self) -> None:
        return None


# --- fixtures ----------------------------------------------------------------


@pytest.fixture
def fake_ctx(tmp_path: Path) -> GenerationContext:
    rb = tmp_path / "rb.md"
    rb.write_text("# rulebook")
    return GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri=str(rb), source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
    )


def _silent_runner(**kwargs: Any) -> ClaudeCodeRunner:
    """Build a runner whose sinks discard streamed output (keeps test stdout clean)."""
    return ClaudeCodeRunner(stdout_sink=lambda _t: None, stderr_sink=lambda _t: None, **kwargs)


# --- is_available -------------------------------------------------------------


def test_is_available_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    healthy, detail = asyncio.run(ClaudeCodeRunner().is_available())
    assert healthy is False
    assert "not found" in detail.lower()


def test_is_available_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _VersionProc:
        returncode = 0

        async def communicate(self, input: bytes | None = None) -> tuple[bytes, bytes]:  # noqa: A002
            return (b"Claude Code v0.1.0", b"")

    async def _exec(*a: Any, **k: Any) -> _VersionProc:
        return _VersionProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    healthy, _detail = asyncio.run(ClaudeCodeRunner().is_available())
    assert healthy is True


# --- generate -----------------------------------------------------------------


def test_generate_raises_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(GraceError) as exc:
        asyncio.run(_silent_runner().generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_NOT_FOUND


def test_generate_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nsleep 60")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    # Build a proc whose wait() hangs longer than the runner's timeout.
    class _HangingProc(_FakeProc):
        async def wait(self) -> int:
            await asyncio.sleep(5.0)
            return 0

    async def _exec(*a: Any, **k: Any) -> _HangingProc:
        return _HangingProc(stdout_bytes=b"", stderr_bytes=b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(_silent_runner(timeout_s=0.05).generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_TIMEOUT


def test_generate_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 2")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    async def _exec(*a: Any, **k: Any) -> _FakeProc:
        return _FakeProc(stdout_bytes=b"bad\n", stderr_bytes=b"auth error\n", returncode=2)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(_silent_runner().generate(fake_ctx))
    assert exc.value.reason in {
        GraceErrorReason.CLAUDE_CODE_FAILED,
        GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED,
    }


def test_generate_streams_stdout_to_sink_live(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    """Lines from claude's stdout should flow through the runner's sink as they
    arrive, not only after the subprocess exits."""
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    async def _exec(*a: Any, **k: Any) -> _FakeProc:
        return _FakeProc(
            stdout_bytes=b"reading rulebook...\ngenerating connector.py...\ndone\n",
            stderr_bytes=b"",
            returncode=0,
        )

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    captured: list[str] = []
    runner = ClaudeCodeRunner(stdout_sink=captured.append, stderr_sink=lambda _t: None)
    result = asyncio.run(runner.generate(fake_ctx))

    assert "reading rulebook...\n" in captured
    assert "generating connector.py...\n" in captured
    assert "done\n" in captured
    # Streamed text is also preserved in the GenerationResult for downstream logging.
    assert "reading rulebook...\n" in result.stdout
