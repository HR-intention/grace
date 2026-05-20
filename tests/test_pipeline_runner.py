from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.runner import ClaudeCodeRunner
from grace.pipeline.types import GenerationContext, PspDocs


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

    class _Proc:
        returncode = 0

        async def communicate(self, input: bytes | None = None) -> tuple[bytes, bytes]:  # noqa: A002
            return (b"Claude Code v0.1.0", b"")

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    healthy, _detail = asyncio.run(ClaudeCodeRunner().is_available())
    assert healthy is True


def test_generate_raises_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner().generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_NOT_FOUND


def test_generate_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nsleep 60")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _Proc:
        returncode: int | None = None

        async def communicate(self, input: bytes | None = None) -> tuple[bytes, bytes]:  # noqa: A002
            raise TimeoutError("simulated")

        def kill(self) -> None:
            return None

        async def wait(self) -> int:
            return -9

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner(timeout_s=0.05).generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_TIMEOUT


def test_generate_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 2")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _Proc:
        returncode = 2

        async def communicate(self, input: bytes | None = None) -> tuple[bytes, bytes]:  # noqa: A002
            return (b"bad", b"auth error")

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner().generate(fake_ctx))
    assert exc.value.reason in {
        GraceErrorReason.CLAUDE_CODE_FAILED,
        GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED,
    }
