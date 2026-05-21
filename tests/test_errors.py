from __future__ import annotations

from grace.errors import GraceError, GraceErrorReason


def test_grace_error_carries_reason_and_detail() -> None:
    e = GraceError(reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND, detail="binary missing")
    assert e.reason is GraceErrorReason.CLAUDE_CODE_NOT_FOUND
    assert e.detail == "binary missing"
    assert "CLAUDE_CODE_NOT_FOUND" in str(e)


def test_grace_error_reasons_locked() -> None:
    expected = {
        "CLAUDE_CODE_NOT_FOUND",
        "CLAUDE_CODE_NOT_AUTHENTICATED",
        "CLAUDE_CODE_TIMEOUT",
        "CLAUDE_CODE_FAILED",
        "CONTEXT_BUNDLE_INVALID",
        "QUALITY_GATE_FAILED",
        "SOURCE_FETCH_FAILED",
        "CONFIG_INVALID",
    }
    assert {r.value for r in GraceErrorReason} == expected
