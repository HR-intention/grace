from __future__ import annotations

from enum import StrEnum


class GraceErrorReason(StrEnum):
    CLAUDE_CODE_NOT_FOUND = "CLAUDE_CODE_NOT_FOUND"
    CLAUDE_CODE_NOT_AUTHENTICATED = "CLAUDE_CODE_NOT_AUTHENTICATED"
    CLAUDE_CODE_TIMEOUT = "CLAUDE_CODE_TIMEOUT"
    CLAUDE_CODE_FAILED = "CLAUDE_CODE_FAILED"
    CONTEXT_BUNDLE_INVALID = "CONTEXT_BUNDLE_INVALID"
    QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"
    SOURCE_FETCH_FAILED = "SOURCE_FETCH_FAILED"
    CONFIG_INVALID = "CONFIG_INVALID"


class GraceError(Exception):
    def __init__(self, *, reason: GraceErrorReason, detail: str | None = None):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason.value}: {detail}" if detail else reason.value)
