from __future__ import annotations

from lens.enums import PaymentAttemptStatus, PaymentFailureCode

STATUS_MAP: dict[str, PaymentAttemptStatus] = {}
FAILURE_MAP: dict[str, PaymentFailureCode] = {}
