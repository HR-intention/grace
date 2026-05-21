# File layout (mandatory)

Verbatim from `SUBPROJECT_GRACE_CODEGEN.md` §3.2. Grace's rubric verifies these files exist; missing files cost rubric points.

```
connectors/<psp>/
  __init__.py            # imports + ConnectorFactory.register("<psp>", <PspClass>)
  connector.py           # class <Psp>(Connector): ...
  auth.py                # signing helpers
  models.py              # PSP-specific wire-level Pydantic models
  status_map.py          # PSP-specific term → (PaymentAttemptStatus, PaymentFailureCode)
                         # per SUBPROJECT_LENS.md §5.2
  tests/
    test_create_order.py
    test_sync_payment.py
    test_refund.py
    test_sync_refund.py
    test_webhook.py
```

## What goes in each file

```
__init__.py     — Module scope: declare requires_lens = "<constraint>".
                  At the bottom: from .connector import <Psp>; ConnectorFactory.register("<psp>", <Psp>).

connector.py    — class <Psp>(Connector). Implements all four flows + handle_webhook + close.
                  Each flow: validate input, build PSP request, call self._client, parse response,
                  return domain response. Wrap httpx.HTTPStatusError -> _map_http_error;
                  httpx.HTTPError -> ConnectorError(PSP_UNAVAILABLE).

auth.py         — signing helpers. Credentials typed Maskable[str]. Function names like
                  sign_request, verify_signature, build_auth_headers. No global state.

models.py       — wire-level Pydantic models. extra="forbid"; frozen=True on request bodies,
                  frozen=False on response bodies. One model per PSP request/response shape.

status_map.py   — PSP-specific status string -> (PaymentAttemptStatus, PaymentFailureCode).
                  Define a single dict; have a function map_status(s: str) -> tuple[..., ...] that
                  returns (PENDING/SUCCESS/FAILED, code-or-None) and falls back to
                  (FAILED, PaymentFailureCode.UNKNOWN) with a structlog.warning for unknown values.

tests/test_create_order.py — happy + 4xx + 5xx + network-error paths, plus a parametrized
                             test of every branch in `_map_http_error`. See testing.md for the
                             full required-case list per file — the 5xx / network-error /
                             error-mapping cases are what keep coverage ≥ 80% once the connector
                             grows a 6+ branch HTTP-error mapper.
tests/test_sync_payment.py — single-attempt + multi-attempt + 5xx + unknown PSP order-status
                             fallback cases.
tests/test_refund.py       — happy + already-refunded + 5xx paths.
tests/test_sync_refund.py  — PENDING + SUCCESS + not-found (404) + malformed-response
                             (ValidationError) paths.
tests/test_webhook.py      — signed PAYMENT_SUCCESS / PAYMENT_FAILED / REFUND_SUCCESS, tampered
                             payload -> ConnectorError(WEBHOOK_SIGNATURE_FAILED), unknown
                             event-type fallback.
```

## Optional / additive files

Extra helper modules (e.g., a custom token-refresh helper) are allowed but don't earn rubric points. They must still carry the §4 marker.

## Notes

- All paths are relative to `lens/connectors/<psp>/`.
- `tests/__init__.py` is optional but harmless.
- Use `from lens.connector import Connector`, `from lens.factory import ConnectorFactory`, `from lens.domain_types import ...`, `from lens.enums import ...`, `from lens.common import Maskable, ConnectorError, ConnectorErrorReason` for imports.
