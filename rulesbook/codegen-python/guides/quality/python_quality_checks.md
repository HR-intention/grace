# Python-specific quality checks

These layer on top of the language-neutral checks in `../../../shared/quality_rubric.md`. The Quality Guardian applies both lists when scoring a Python connector.

## Critical (deduct 20 points each)

- All public connector methods are `async def`.
- `@connector_flow(flow=Flow.<NAME>)` is applied to every flow method (Authorize, PSync, Capture, Refund, RSync, Void). Missing decorator = no logging / no error normalization.
- PSP-specific Pydantic models use `model_config = ConfigDict(extra="forbid")`.
- `register_connector("{connector}", {Connector})` is called from the connector's `__init__.py`.
- The connector module is imported from `connector_service/connectors/__init__.py` (explicit-discovery convention from Plan C).
- `mypy --strict connector_service/connectors/{connector}/` passes.
- No floats on money. `Amount.minor_units` is always `int`.
- No bare `except:` — catch specific exception types.
- No synchronous I/O (`requests`, `time.sleep`, `urllib.request`) in async paths.
- `httpx.AsyncClient` is reused via `self.client`, not constructed per call.
- PCI/PII fields (card_number, cvv, vpa) are never logged in plaintext. Use field names that the masking processor catches, or call `mask_*` helpers explicitly.
- Webhook signature verification uses `hmac.compare_digest` (constant-time).
- IncomingWebhook implementations call `WebhookEvent.duplicate(...)` when the event has been seen before (or rely on router-layer dedup).

## Warnings (deduct 5 points each)

- `await self.client.aclose()` is wired into `BaseConnector.aclose` (it is by default; flag if overridden).
- Uses `logging` / `structlog` rather than `print()`.
- Type hints are present on every method signature, including helpers.
- `from __future__ import annotations` is used (consistent with Plan C code style).
- Status mapping helpers (`_map_status`) are present, exhaustive, and raise on unknown statuses (rather than defaulting silently).
- Errors include connector-provided message + code (use `connector_status_code` on `ConnectorError`).

## Suggestions (deduct 1 point each)

- Per-connector `*Auth` class is well-named (e.g., `RazorpayAuth`, not `MyAuth`).
- Transformer functions are pure (no side effects, no `self`).
- Tests are marked `@pytest.mark.integration` so they can be skipped without credentials.
- Comments are sparse and used only where the WHY isn't obvious from code.

## Cross-cutting checks (see ../../../shared/quality_rubric.md)

Applied to every language. Summarized here for reference:
- Idempotency key sent on Authorize/Capture/Refund (the `@connector_flow` decorator handles this for Python).
- Every documented PSP status mapped (no silent fallthrough).
- No hardcoded secrets.
- All flows requested have real implementations (no `NotImplementedError`).
- Webhook signature verification + dedup (if IncomingWebhook implemented).
- Currency/amount uses minor-unit-aware helpers.
- PCI/PII masking applied to log lines.

## Scoring

Per the shared rubric: `Quality Score = 100 - (Critical × 20) - (Warnings × 5) - (Suggestions × 1)`. Gate: ≥ 60.
