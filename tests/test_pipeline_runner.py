from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.runner import (
    ClaudeCodeRunner,
    _extract_result_stats,
    format_stream_event,
)
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
        reports_dir=tmp_path / "_reports",
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


def test_format_stream_event_system_init() -> None:
    line = '{"type":"system","subtype":"init","model":"claude-x","tools":["Read","Write"]}'
    out = format_stream_event(line)
    assert out is not None
    assert "session started" in out
    assert "model=claude-x" in out
    assert "2 tools" in out


def test_format_stream_event_assistant_tool_use() -> None:
    line = (
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read",'
        '"input":{"file_path":"/tmp/x.md"}}]}}'
    )
    out = format_stream_event(line)
    assert out is not None
    assert "→ Read(/tmp/x.md)" in out


def test_format_stream_event_assistant_text_emits_text() -> None:
    line = '{"type":"assistant","message":{"content":[{"type":"text","text":"working on it"}]}}'
    out = format_stream_event(line)
    assert out is not None
    assert "working on it" in out


def test_format_stream_event_result_summary() -> None:
    line = (
        '{"type":"result","subtype":"success","total_cost_usd":0.0042,'
        '"duration_ms":12345,"is_error":false}'
    )
    out = format_stream_event(line)
    assert out is not None
    assert "done" in out
    assert "cost=$0.0042" in out
    assert "duration=12.3s" in out


def test_format_stream_event_passes_through_non_json() -> None:
    line = "Loading Claude Code v2.1.118\n"
    out = format_stream_event(line)
    assert out == line


def test_format_stream_event_skips_blank() -> None:
    assert format_stream_event("\n") is None
    assert format_stream_event("") is None


def test_format_stream_event_skips_hook_events() -> None:
    # SessionStart hook firing — pure noise to the user, kept only in raw buffer.
    line = (
        '{"type":"system","subtype":"hook_started","hook_id":"x","hook_name":"SessionStart:startup"}'
    )
    assert format_stream_event(line) is None
    line2 = '{"type":"system","subtype":"hook_response","hook_id":"x","output":"...huge..."}'
    assert format_stream_event(line2) is None


def test_format_stream_event_skips_rate_limit() -> None:
    line = '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed"}}'
    assert format_stream_event(line) is None


def test_format_stream_event_skips_status_and_compact_boundary() -> None:
    """New noisy event types observed in real claude runs."""
    assert format_stream_event('{"type":"system","subtype":"status"}') is None
    assert format_stream_event('{"type":"system","subtype":"compact_boundary"}') is None


def test_extract_result_stats_pulls_cost_and_duration() -> None:
    lines = [
        '{"type":"assistant","message":{"content":[]}}\n',
        '{"type":"result","subtype":"success","total_cost_usd":4.5968,"duration_ms":883500}\n',
    ]
    cost, dur = _extract_result_stats(lines)
    assert cost == 4.5968
    assert dur == 883500


def test_extract_result_stats_returns_none_when_absent() -> None:
    cost, dur = _extract_result_stats(['{"type":"system","subtype":"init"}\n'])
    assert cost is None
    assert dur is None


def test_format_stream_event_unknown_type_emits_short_marker() -> None:
    line = '{"type":"future_thing","subtype":"weird","payload":"' + ("X" * 5000) + '"}'
    out = format_stream_event(line)
    assert out is not None
    assert "unknown event: future_thing/weird" in out
    # Crucially: must not dump the huge payload.
    assert len(out) < 200


def test_format_stream_event_tool_use_write_includes_size() -> None:
    line = (
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Write",'
        '"input":{"file_path":"/tmp/connector.py","content":"hello world"}}]}}'
    )
    out = format_stream_event(line)
    assert out is not None
    assert "Write(/tmp/connector.py, 11B)" in out


def test_generate_passes_add_dir_for_rulebook_and_psp_docs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every directory containing a rulebook file or PSP doc must be granted
    via `--add-dir` so Claude can read them from cwd=output_dir."""
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    rb_dir = tmp_path / "grace_repo" / "rulesbook" / "codegen" / "python"
    rb_dir.mkdir(parents=True)
    rb_file = rb_dir / "connector_abc.md"
    rb_file.write_text("# rulebook")

    docs_dir = tmp_path / "lens_repo" / "connector_docs" / "cashfree"
    docs_dir.mkdir(parents=True)
    docs_file = docs_dir / "01_orders.md"
    docs_file.write_text("# psp docs")

    ctx = GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[rb_file],
        psp_docs=PspDocs(
            source_uri=str(docs_dir), source_kind="local_dir", local_paths=[docs_file]
        ),
        output_dir=tmp_path / "lens_repo" / "lens" / "connectors" / "cashfree",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
        reports_dir=tmp_path / "_reports",
    )

    captured_args: list[str] = []

    async def _exec(*args: Any, **k: Any) -> _FakeProc:
        captured_args.extend(args)
        return _FakeProc(stdout_bytes=b"", stderr_bytes=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    asyncio.run(_silent_runner().generate(ctx))

    # The argv now contains --add-dir <X> pairs. Verify both the rulebook
    # parent and the psp-docs parent are present.
    assert "--add-dir" in captured_args
    add_dir_values = [
        captured_args[i + 1]
        for i, a in enumerate(captured_args[:-1])
        if a == "--add-dir"
    ]
    assert any(str(rb_dir) == v or str(rb_dir.parent) in v for v in add_dir_values)
    assert any(str(docs_dir) == v or str(docs_dir.parent) in v for v in add_dir_values)


def test_generate_handles_oversized_line_without_crash(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    """A readline ValueError on one oversized event must not kill the stream;
    the rest of the run should still flow through."""
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    # A custom reader that raises ValueError on the second readline (mimicking
    # asyncio's behaviour for a line that overruns the limit), then yields
    # the next event normally.
    class _LimitOverrunReader:
        def __init__(self, lines: list[bytes]) -> None:
            self._lines = lines
            self._idx = 0

        async def readline(self) -> bytes:
            if self._idx >= len(self._lines):
                return b""
            item = self._lines[self._idx]
            self._idx += 1
            if item == b"<RAISE>":
                raise ValueError("Separator is not found, and chunk exceed the limit")
            return item

    class _Proc(_FakeProc):
        pass

    proc = _Proc(stdout_bytes=b"", stderr_bytes=b"", returncode=0)
    proc.stdout = _LimitOverrunReader(  # type: ignore[assignment]   # test stub
        [
            b'{"type":"system","subtype":"init","model":"x","tools":[]}\n',
            b"<RAISE>",
            b'{"type":"result","subtype":"success","duration_ms":1,"total_cost_usd":0.0}\n',
        ]
    )

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    captured: list[str] = []
    runner = ClaudeCodeRunner(stdout_sink=captured.append, stderr_sink=lambda _t: None)
    # Must not raise.
    asyncio.run(runner.generate(fake_ctx))

    joined = "".join(captured)
    assert "session started" in joined            # event before the overrun came through
    assert "oversized stream event skipped" in joined  # marker landed
    assert "done" in joined                        # event after the overrun came through


def test_generate_streams_stdout_to_sink_live(
    monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path
) -> None:
    """Lines from claude's stdout should flow through the runner's sink as they
    arrive, not only after the subprocess exits."""
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    # Simulate `claude -p --output-format stream-json --verbose` output: three
    # JSONL events arrive over time and each gets formatted.
    jsonl = (
        b'{"type":"system","subtype":"init","model":"claude-x","tools":["Read"]}\n'
        b'{"type":"assistant","message":{"content":['
        b'{"type":"tool_use","name":"Read","input":{"file_path":"/tmp/rb.md"}}'
        b']}}\n'
        b'{"type":"result","subtype":"success","total_cost_usd":0.001,"duration_ms":100}\n'
    )

    async def _exec(*a: Any, **k: Any) -> _FakeProc:
        return _FakeProc(stdout_bytes=jsonl, stderr_bytes=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    captured: list[str] = []
    runner = ClaudeCodeRunner(stdout_sink=captured.append, stderr_sink=lambda _t: None)
    result = asyncio.run(runner.generate(fake_ctx))

    # The formatter turned each JSONL event into a human-readable line that hit
    # the sink as it arrived.
    joined = "".join(captured)
    assert "session started" in joined
    assert "Read(/tmp/rb.md)" in joined
    assert "done" in joined
    # Raw transcript is preserved for error scanning + GenerationResult.
    assert '"type":"system"' in result.stdout
