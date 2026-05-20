from __future__ import annotations

from grace.pipeline.types import GenerationContext


PROMPT_TEMPLATE = """\
You are generating a Python PSP connector for the Orbit Lens.

Target package layout (you will create these files in the current working directory):

  __init__.py
  connector.py
  auth.py
  models.py
  status_map.py
  tests/__init__.py
  tests/test_create_order.py
  tests/test_sync_payment.py
  tests/test_refund.py
  tests/test_sync_refund.py
  tests/test_webhook.py

╔══════════════════════════════════════════════════════════════════════╗
║ LOCKED SURFACE — DO NOT DEVIATE                                       ║
╚══════════════════════════════════════════════════════════════════════╝

These are the most common ways a generation can go wrong. Read them BEFORE
reading the rulebook, then re-check against this list before you finish.

1. CLASS NAME is the PSP name in PascalCase, with **no `Connector` suffix**.
   ✓ `class Cashfree(Connector):`        — for PSP `cashfree`
   ✗ `class CashfreeConnector(Connector):`
   ✗ `class CashfreeClient(Connector):`

2. IMPORTS come from these exact module paths:
     from lens.connector import Connector
     from lens.factory import ConnectorFactory, ConnectorConfig
     from lens.domain_types import (
         CreateOrderRequest, CreateOrderResponse,
         SyncPaymentRequest, SyncPaymentResponse,
         RefundRequest, RefundResponse,
         SyncRefundRequest, SyncRefundResponse,
         PaymentAttempt, RefundEvent, WebhookEvent,
         Amount,
     )
     from lens.enums import (
         Currency, PaymentMethod,
         OrderStatus, PaymentAttemptStatus, RefundStatus,
         PaymentFailureCode, WebhookEventType, ConnectorErrorReason,
     )
     from lens.common import Maskable, ConnectorError
   ✗ Do NOT import from `lens.connector_abc`, `lens.types`, `lens.models`, etc.
   ✗ Do NOT import a `Money` type — the locked money type is `Amount`.

3. EVERY FLOW METHOD IS `async def`. Use `httpx.AsyncClient`. Ground rule 3.
   ✓ `async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:`
   ✗ `def create_order(self, request): ...`

3a. THE CLASS DECLARES ALL FOUR ABSTRACT `@property`s. If any of these are
    missing, `ConnectorFactory.register(...)` at import time raises
    `Can't instantiate abstract class <Psp> without an implementation for
    abstract methods 'base_url', 'name', 'supported_methods',
    'supports_idempotency_key'` and your tests can't even collect. Write
    ALL FOUR — they're cheap one-liners:

      @property
      def name(self) -> str:
          return "<psp>"                            # MUST match the registry key

      @property
      def base_url(self) -> str:
          return "https://sandbox.<psp>.com/..."    # PSP's sandbox base URL

      @property
      def supported_methods(self) -> set[PaymentMethod]:
          return {{PaymentMethod.CARD, PaymentMethod.UPI}}   # subset PSP supports

      @property
      def supports_idempotency_key(self) -> bool:
          return True                               # True iff the PSP honors the header

    These come BEFORE the async flow methods in `class <Psp>(Connector):`.

4. DOMAIN TYPES use the **exact** field names from `domain_types.md`. Pydantic
   models are `extra="forbid"` — invented fields error out at construction.
   - `request.amount.minor_units: int`            (NOT `.value`, NOT `.amount`)
   - `request.amount.currency: Currency`
   - `request.customer_id: str | None`            (NOT `request.customer.id`, NOT a nested object)
   - `request.idempotency_key: str | None`
   - `request.merchant_id: str`                   (required — comes from ConnectorConfig)
   - `request.return_url: HttpUrl`                (required for create_order)
   - `request.order_id: str`                      (Orbit's UUID — required)

   Response fields are locked. Do NOT invent extras (`raw`, `connector_order_id`, etc.).
   - `CreateOrderResponse`:  psp_order_id, payment_link, status, expires_at
   - `SyncPaymentResponse`:  psp_order_id, status, paid_amount, attempts
   - `RefundResponse`:       psp_refund_id, status, refunded_amount
   - `SyncRefundResponse`:   psp_refund_id, status, refunded_amount, failure_reason
   - `PaymentAttempt`:       psp_payment_id, status, method_used, amount,
                             failure_code, failure_reason, attempted_at, raw

   ✓ `return CreateOrderResponse(psp_order_id=..., payment_link=..., status=OrderStatus.CREATED)`
   ✗ `return CreateOrderResponse(order_id=..., connector_order_id=..., raw={{...}})`  ← will fail mypy AND Pydantic
   ✗ No `float()` conversions anywhere on the domain surface (ground rule 10).

5. `__init__.py` MUST do two things at module scope:
     requires_lens = "{lens_version_constraint}"
     from .connector import <Psp>
     from lens.factory import ConnectorFactory
     ConnectorFactory.register("<psp>", <Psp>)
   ✗ Don't just `__all__ = [...]` and call it done.

6. CREDENTIALS in `auth.py` are typed `Maskable[str]`, not bare `str`.
     api_key: Maskable[str]
     secret_key: Maskable[str]
   Read with `.expose()` only inside the HTTP call (never log the result).
   ✗ Do NOT define a `<Psp>Config` dataclass. The config type is `lens.factory.ConnectorConfig`.

7. WEBHOOK SIGNATURE FAILURE raises a typed error, not `ValueError`:
     raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)
   ✗ `raise ValueError("bad signature")` will score 0 on error_handling.

8. STATUS ENUMS are LOCKED — you may NOT add new values:
   - PaymentAttemptStatus = PENDING | SUCCESS | FAILED                  (three values, no more)
   - RefundStatus         = PENDING | SUCCESS | FAILED
   - OrderStatus          = CREATED | PAID | PARTIALLY_REFUNDED | REFUNDED | EXPIRED | FAILED
   ✗ NO `CAPTURED`, `AUTHORIZED`, `CANCELLED`, `VOID`, `REJECTED`, etc.
     If the PSP has those terms, map them via status_map.py into PENDING/SUCCESS/FAILED
     + a PaymentFailureCode.

9. FAILURE CODES come from this exact list (PaymentFailureCode enum):
   USER_DROPPED, USER_CANCELLED, CARD_DECLINED, INSUFFICIENT_FUNDS,
   AUTHENTICATION_FAILED, FRAUD_BLOCKED, FRAUD_REVIEW_PENDING,
   INVALID_INSTRUMENT, PSP_ERROR, NETWORK_ERROR, UNKNOWN.
   ✗ NO `PAYMENT_DECLINED`, `CUSTOMER_CANCELLED`, `EXPIRED_CARD`, `TIMEOUT`, etc.

10. MARKER BLOCK at the very top of each .py file is **the only** doc-header.
    Grace writes the marker for you if you forget; do NOT also write your own
    `# Code generated by ... DO NOT EDIT` comment — that ends up duplicated.

11. HTTP CLIENT lifecycle:
    - Build `httpx.AsyncClient(...)` in `__init__`. Owned by the Connector.
    - Close it in `async def close(self) -> None: await self._client.aclose()`.
    - Tests inject a mock via `httpx.MockTransport`.

╔══════════════════════════════════════════════════════════════════════╗
║ POST-GENERATION SELF-CHECK                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Before you exit, grep your own output for these and verify each one matches:

  STRUCTURE:
    $ grep -E "^class [A-Z][a-z]+\\(Connector\\)" connector.py        # exactly one match
    $ grep "from lens.connector import Connector" connector.py         # present
    $ grep "ConnectorFactory.register" __init__.py                      # present
    $ grep "requires_lens" __init__.py                                  # present
    $ grep -c "async def" connector.py                                  # >= 6 (5 flows + close)
    $ grep -c "@property" connector.py                                  # >= 4
    $ grep -E "def name|def base_url|def supported_methods|def supports_idempotency_key" connector.py  # 4 matches

  PII + ERRORS:
    $ grep "Maskable" auth.py                                           # at least once
    $ grep "WEBHOOK_SIGNATURE_FAILED" connector.py                      # at least once
    $ grep -E "Money|float\\(" connector.py models.py                   # ZERO matches

  LOCKED FIELD NAMES (every one of these has been gotten wrong by past
  generations — verify ALL six lines in your own output before exiting):

    $ grep -E "config\\.credentials|config\\.merchant_id" connector.py auth.py  # ZERO
                            # ConnectorConfig has api_key/secret_key/webhook_secret;
                            # merchant_id lives on requests, not config.

    $ grep -E "\\bpayment_attempt=|\\brefund_event=" connector.py tests/*.py   # ZERO
                            # WebhookEvent fields are `attempt` and `refund`.

    $ grep -E "WebhookEvent\\(.*payment_attempt|WebhookEvent\\(.*refund_event" *.py  # ZERO

    $ grep -E "\\.payment_attempt\\b|\\.refund_event\\b" tests/*.py             # ZERO
                            # event.attempt / event.refund, never the longer names.

    $ grep -E "RefundRequest\\(.*\\bamount=" connector.py tests/*.py            # ZERO
                            # RefundRequest has amount_to_refund: int|None; no `amount` field.

    $ grep -E "SyncRefundRequest\\(.*\\brefund_id=|SyncRefundRequest\\(.*\\bpsp_order_id=" \\
        connector.py tests/*.py                                                  # ZERO
                            # SyncRefundRequest takes only psp_refund_id + RequestCommon.

    $ grep -E "RefundResponse\\(.*refunded_amount=Amount|SyncRefundResponse\\(.*refunded_amount=Amount" \\
        connector.py                                                              # ZERO
                            # refunded_amount is int (minor units), never Amount.

    $ grep -E "SyncPaymentResponse\\(.*paid_amount=Amount" connector.py           # ZERO
                            # paid_amount is int (minor units), never Amount.

    $ grep -E "PaymentAttempt\\(.*attempted_at=None" connector.py                 # ZERO
                            # attempted_at is required, non-optional.

    $ grep -E "\\border_id=[^,)]" connector.py | grep -v "request\\.order_id"     # ZERO matches
                            # No invented order_id= kwarg on responses; pass psp_order_id.

    $ grep -E "CreateOrderResponse\\(.*payment_link=str|payment_link=str\\(" connector.py  # ZERO
                            # payment_link is HttpUrl. Coerce via HttpUrl(s) or use a typed
                            # Pydantic field that returns HttpUrl directly.

  TEST FIXTURES:
    $ grep -E "ConnectorConfig\\(.*credentials=|ConnectorConfig\\(.*merchant_id=" tests/*.py   # ZERO
                            # ConnectorConfig takes name=, api_key=, secret_key=, webhook_secret=.

    $ grep -E "(CreateOrderRequest|SyncPaymentRequest|RefundRequest|SyncRefundRequest)\\(" tests/*.py \\
        | head -3                                                                 # must include merchant_id= and order_id=
                            # Every request needs both RequestCommon fields supplied.

    $ grep -cE "^(async )?def test_[a-z_]+\\(.*\\) ->" tests/*.py                  # every test fn returns -> None
                            # mypy --strict requires explicit -> None on async def test_x():

  CONSTRUCTOR + WEBHOOK SHAPE:
    $ grep -nE "\\.expose\\(\\)" connector.py | grep -E "def __init__|self\\._client = httpx" -A 5 -B 2  # ZERO calls to .expose() in __init__ block
                            # __init__ stores config, builds client. NEVER call .expose() there —
                            # ConnectorFactory.register passes a stub_config with None creds at
                            # register time. Build headers inside the flow methods at HTTP call time.

    $ grep -E "async def handle_webhook\\(self, raw_payload: bytes, headers: dict\\[str, str\\]\\) -> WebhookEvent:" connector.py  # exactly one match
                            # Signature must match the ABC verbatim — no renaming, no widening.

    $ grep -E "WebhookEvent\\(" connector.py | grep -v "psp_event_id" | wc -l    # ZERO
                            # Every WebhookEvent(...) construction must include psp_event_id=.

    $ grep -E "WebhookEvent\\(" connector.py | grep -v "raw_payload" | wc -l     # ZERO
                            # Every WebhookEvent(...) construction must include raw_payload=.

    $ grep -E "PaymentAttempt\\(.*amount=[0-9]+|PaymentAttempt\\(.*amount=request\\." connector.py  # ZERO
                            # PaymentAttempt.amount is Amount|None (the ONE exception to int-minor-units).
                            # Wrap raw int as Amount(minor_units=N, currency=Currency.X).

  If ANY check above has a non-empty match (when it should be ZERO) or a
  missing match (when it should be present), fix it before writing the
  final file out.

╔══════════════════════════════════════════════════════════════════════╗
║ CONTEXT FILES                                                         ║
╚══════════════════════════════════════════════════════════════════════╝

Read these in order — `ground_rules.md` first, then the type contracts, then
the per-flow patterns. Re-read `connector_abc.md` whenever in doubt about a
method signature.

{rulebook_block}

╔══════════════════════════════════════════════════════════════════════╗
║ PSP DOCUMENTATION                                                     ║
╚══════════════════════════════════════════════════════════════════════╝

{source_block}

╔══════════════════════════════════════════════════════════════════════╗
║ THIS RUN                                                              ║
╚══════════════════════════════════════════════════════════════════════╝

Target module: {target_module}
Generator version: grace {grace_version}
Source version: {source_version}
Lens version constraint: {lens_version_constraint}

Generate the package. Do not ask follow-up questions. Write the files, run
the post-generation self-check above against your own output, then exit.
"""


def build_prompt(ctx: GenerationContext) -> str:
    rulebook_block = "\n".join(f"  - {p}" for p in ctx.rulebook_paths)
    if ctx.psp_docs.source_kind == "url":
        source_block = (
            f"  - URL: {ctx.psp_docs.source_uri}\n"
            f"  - Content fetched at generation time "
            f"(use the Read tool on the cached file: see CWD)."
        )
    else:
        source_block = "\n".join(f"  - {p}" for p in ctx.psp_docs.local_paths)
    return PROMPT_TEMPLATE.format(
        rulebook_block=rulebook_block,
        source_block=source_block,
        target_module=ctx.target_module,
        grace_version=ctx.grace_version,
        source_version=ctx.source_version,
        lens_version_constraint=ctx.lens_version_constraint,
    )
