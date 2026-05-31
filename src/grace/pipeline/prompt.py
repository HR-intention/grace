from __future__ import annotations

from grace.pipeline.types import GenerationContext


# ---------------------------------------------------------------------------
# Domain-conditional file-list blocks
# ---------------------------------------------------------------------------

_FILE_LIST_CORE = """\
  core/base.py          # _<Psp>Base(Connector): name, base_url, close, __init__ + _client
  core/auth.py          # build_auth_headers + verify_signature (HMAC, family-agnostic)
  core/status.py        # failure free-text -> (PaymentFailureCode, FailureClass)
  core/models.py        # shared wire models (webhook envelope, error body)"""

_FILE_LIST_ORDERS = """\
  orders/connector.py   # class <Psp>Orders(_<Psp>Base, PaymentsConnector)
  orders/models.py      # payment wire models
  orders/status_map.py  # PSP payment status -> (PaymentAttemptStatus, PaymentFailureCode)
  orders/webhooks.py    # _parse_payment_webhook(raw: bytes) -> PaymentWebhookEvent
  tests/integration/connectors/<psp>/orders/test_create_order.py
  tests/integration/connectors/<psp>/orders/test_sync_payment.py
  tests/integration/connectors/<psp>/orders/test_refund.py
  tests/integration/connectors/<psp>/orders/test_sync_refund.py"""

_FILE_LIST_SUBSCRIPTIONS = """\
  subscriptions/connector.py   # class <Psp>Subscriptions(_<Psp>Base, MandateConnector)
  subscriptions/models.py      # subscription / plan / mandate wire models
  subscriptions/status_map.py  # PSP subscription_status -> MandateStatus; event -> WebhookEventType
  subscriptions/webhooks.py    # _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent
  tests/integration/connectors/<psp>/subscriptions/test_create_subscription.py
  tests/integration/connectors/<psp>/subscriptions/test_sync_subscription.py
  tests/integration/connectors/<psp>/subscriptions/test_cancel_subscription.py
  tests/integration/connectors/<psp>/subscriptions/test_pause_subscription.py
  tests/integration/connectors/<psp>/subscriptions/test_resume_subscription.py"""

_FILE_LIST_WEBHOOK_ROUTER_TEST = """\
  tests/integration/connectors/<psp>/test_webhook_router.py"""

_FILE_LIST_ALL = (
    _FILE_LIST_CORE
    + "\n"
    + _FILE_LIST_ORDERS
    + "\n"
    + _FILE_LIST_SUBSCRIPTIONS
    + "\n"
    + _FILE_LIST_WEBHOOK_ROUTER_TEST
)


# ---------------------------------------------------------------------------
# Domain-conditional import blocks
# ---------------------------------------------------------------------------

_IMPORTS_COMMON = """\
     from lens.connector import Connector
     from lens.webhook import WebhookHandlers, WebhookFamily
     from lens.factory import ConnectorFactory, ConnectorConfig
     from lens.common import Maskable, ConnectorError, ConnectorErrorReason"""

_IMPORTS_ORDERS = """\
     from lens.payments_connector import PaymentsConnector
     from lens.domain_types import (
         CreateOrderRequest, CreateOrderResponse,
         SyncPaymentRequest, SyncPaymentResponse,
         RefundRequest, RefundResponse,
         SyncRefundRequest, SyncRefundResponse,
         PaymentAttempt, PaymentWebhookEvent,
         Amount,
     )
     from lens.enums import (
         Currency, PaymentMethod,
         PaymentAttemptStatus, OrderStatus, RefundStatus,
         PaymentFailureCode, FailureClass, FAILURE_CLASS,
         WebhookEventType, ConnectorErrorReason,
     )"""

_IMPORTS_SUBSCRIPTIONS = """\
     from lens.mandate_connector import MandateConnector
     from lens.domain_types import (
         CreateSubscriptionRequest, CreateSubscriptionResponse,
         SyncSubscriptionRequest, SyncSubscriptionResponse,
         ManageMandateRequest, ManageMandateResponse,
         MandateWebhookEvent,
         Amount,
     )
     from lens.enums import (
         MandateRail, MandateStatus, MandateIntervalType, MandateDebitStatus,
         PaymentFailureCode, FailureClass, FAILURE_CLASS,
         WebhookEventType, ConnectorErrorReason,
     )"""

_IMPORTS_ALL = """\
     from lens.payments_connector import PaymentsConnector
     from lens.mandate_connector import MandateConnector
     from lens.domain_types import (
         CreateOrderRequest, CreateOrderResponse,
         SyncPaymentRequest, SyncPaymentResponse,
         RefundRequest, RefundResponse,
         SyncRefundRequest, SyncRefundResponse,
         PaymentAttempt, PaymentWebhookEvent,
         CreateSubscriptionRequest, CreateSubscriptionResponse,
         SyncSubscriptionRequest, SyncSubscriptionResponse,
         ManageMandateRequest, ManageMandateResponse,
         MandateWebhookEvent,
         Amount,
     )
     from lens.enums import (
         Currency, PaymentMethod,
         MandateRail, MandateStatus, MandateIntervalType, MandateDebitStatus,
         PaymentAttemptStatus, OrderStatus, RefundStatus,
         PaymentFailureCode, FailureClass, FAILURE_CLASS,
         WebhookEventType, ConnectorErrorReason,
     )"""


# ---------------------------------------------------------------------------
# Domain-conditional class-shape blocks
# ---------------------------------------------------------------------------

_CLASS_SHAPE_CORE = """\
core/base.py — _<Psp>Base(Connector)
   The private shared base class. Owns identity + lifecycle for all domain mixins:

     class _<Psp>Base(Connector):
         @property
         def name(self) -> str: return "<psp>"           # MUST match registry key

         @property
         def base_url(self) -> str: return "<PSP_SANDBOX_URL>"

         def __init__(self, config: ConnectorConfig) -> None:
             self._config = config
             self._client = httpx.AsyncClient(
                 base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
                 timeout=30.0,
             )

         async def close(self) -> None:
             await self._client.aclose()

   ONE httpx.AsyncClient per instance, built in _<Psp>Base.__init__, shared by all mixins.
   NEVER build a second client in a domain mixin."""

_CLASS_SHAPE_ORDERS = """\
orders/connector.py — <Psp>Orders(_<Psp>Base, PaymentsConnector)
   Implements the two payment @property introspections and four async flows:

     class <Psp>Orders(_<Psp>Base, PaymentsConnector):
         @property
         def supported_methods(self) -> set[PaymentMethod]: ...
         @property
         def supports_idempotency_key(self) -> bool: ...

         async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse: ...
         async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse: ...
         async def refund(self, request: RefundRequest) -> RefundResponse: ...
         async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse: ...

   Do NOT add extra parameters or change return types (ABC contracts are locked).

orders/webhooks.py — _parse_payment_webhook
   Parses an already-verified raw payload into the domain event:

     def _parse_payment_webhook(raw: bytes) -> PaymentWebhookEvent: ...

   The WebhookRouter calls verify first; this function only normalises bytes into the
   typed domain event. Raise ConnectorError(reason=INVALID_REQUEST) on JSON parse failure."""

_CLASS_SHAPE_SUBSCRIPTIONS = """\
subscriptions/connector.py — <Psp>Subscriptions(_<Psp>Base, MandateConnector)
   NOTE: MandateConnector is SINGULAR — MandatesConnector does not exist.
   Implements 4 introspection methods (plain def, NOT @property, NOT async) + 5 async lifecycle:

     class <Psp>Subscriptions(_<Psp>Base, MandateConnector):
         # --- 4 introspection methods (plain def, no @property, no async) ---
         def supported_mandate_rails(self) -> set[MandateRail]: ...
         def supports_pause(self) -> bool: ...
         def supported_intervals(self) -> set[MandateIntervalType]: ...
         def max_mandate_amount(self, rail: MandateRail) -> Amount | None: ...

         # --- 5 lifecycle methods (async) ---
         async def create_subscription(self, request: CreateSubscriptionRequest) -> CreateSubscriptionResponse: ...
         async def sync_subscription(self, request: SyncSubscriptionRequest) -> SyncSubscriptionResponse: ...
         async def cancel_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...
         async def pause_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...
         async def resume_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...

subscriptions/webhooks.py — _parse_mandate_webhook
   Parses an already-verified raw payload into the mandate domain event:

     def _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent: ...

   The WebhookRouter calls verify first; this function only normalises bytes into the
   typed domain event. Raise ConnectorError(reason=INVALID_REQUEST) on JSON parse failure."""


# ---------------------------------------------------------------------------
# Domain-conditional self-check blocks
# ---------------------------------------------------------------------------

_SELF_CHECK_CORE = """\
  SHARED BASE:
    Grep(pattern="_<Psp>Base", path=<cwd>/core, glob="base.py")
        → present
    Grep(pattern="from lens.connector import Connector", path=<cwd>/core, glob="base.py")
        → present
    Grep(pattern="httpx.AsyncClient", path=<cwd>/core, glob="base.py")
        → exactly one match
    Grep(pattern="async def close", path=<cwd>/core, glob="base.py")
        → present

  AUTHENTICATION:
    Grep(pattern="Maskable", path=<cwd>/core, glob="auth.py")
        → at least one match
    Grep(pattern="hmac.compare_digest", path=<cwd>/core, glob="auth.py")
        → present
    Grep(pattern="WEBHOOK_SIGNATURE_FAILED", path=<cwd>, glob="*.py", output_mode="count")
        → at least one match (in webhooks.py or core/auth.py)"""

_SELF_CHECK_ORDERS = """\
  ORDERS CONNECTOR:
    Grep(pattern="class \\w+Orders(_\\w+Base, PaymentsConnector)", path=<cwd>/orders, glob="connector.py", output_mode="content")
        → exactly one match
    Grep(pattern="from lens.payments_connector import PaymentsConnector", path=<cwd>/orders, glob="connector.py")
        → present
    Grep(pattern="async def", path=<cwd>/orders, glob="connector.py", output_mode="count")
        → >= 4 (four async flow methods)
    Grep(pattern="@property", path=<cwd>/orders, glob="connector.py", output_mode="count")
        → >= 2 (supported_methods + supports_idempotency_key)
    Grep(pattern="def _parse_payment_webhook", path=<cwd>/orders, glob="webhooks.py")
        → present
    Grep(pattern="PaymentWebhookEvent", path=<cwd>/orders, glob="webhooks.py")
        → present

  ORDERS LOCKED FIELD NAMES:
    Grep(pattern="request\\.amount\\.minor_units", path=<cwd>/orders, glob="*.py")
        → at least one match  (not .value, not .amount)
    Grep(pattern="float\\(", path=<cwd>, glob="*.py")
        → ZERO matches
    Grep(pattern="Money", path=<cwd>, glob="*.py")
        → ZERO matches
    Grep(pattern="RefundRequest\\(.*\\bamount=", path=<cwd>, glob="*.py")
        → ZERO matches  (RefundRequest has amount_to_refund: int|None, no `amount`)
    Grep(pattern="SyncPaymentResponse\\(.*paid_amount=Amount", path=<cwd>, glob="*.py")
        → ZERO matches  (paid_amount is int minor units, never Amount)

  ORDERS TESTS:
    Grep(pattern="^(async )?def test_[a-z_]+\\(", path=<cwd>/tests/integration/connectors, glob="*.py", output_mode="content")
        → every match line must end with ") -> None:"
    Grep(pattern="ConnectorConfig\\(.*credentials=|ConnectorConfig\\(.*merchant_id=", path=<cwd>/tests, glob="*.py")
        → ZERO matches  (ConnectorConfig takes name=, api_key=, secret_key=, webhook_secret=)"""

_SELF_CHECK_SUBSCRIPTIONS = """\
  SUBSCRIPTIONS CONNECTOR:
    Grep(pattern="class \\w+Subscriptions(_\\w+Base, MandateConnector)", path=<cwd>/subscriptions, glob="connector.py", output_mode="content")
        → exactly one match
    Grep(pattern="from lens.mandate_connector import MandateConnector", path=<cwd>/subscriptions, glob="connector.py")
        → present
    Grep(pattern="async def", path=<cwd>/subscriptions, glob="connector.py", output_mode="count")
        → >= 5 (five async lifecycle methods)
    Grep(pattern="def supported_mandate_rails\\|def supports_pause\\|def supported_intervals\\|def max_mandate_amount", path=<cwd>/subscriptions, glob="connector.py", output_mode="count")
        → 4 matches  (plain def, NOT @property, NOT async def)
    Grep(pattern="def _parse_mandate_webhook", path=<cwd>/subscriptions, glob="webhooks.py")
        → present
    Grep(pattern="MandateWebhookEvent", path=<cwd>/subscriptions, glob="webhooks.py")
        → present

  SUBSCRIPTIONS LOCKED:
    Grep(pattern="MandatesConnector", path=<cwd>, glob="*.py")
        → ZERO matches  (class is MandateConnector singular, not MandatesConnector)

  SUBSCRIPTIONS TESTS:
    Grep(pattern="^(async )?def test_[a-z_]+\\(", path=<cwd>/tests/integration/connectors, glob="*.py", output_mode="content")
        → every match line must end with ") -> None:"

  WEBHOOK ROUTER TEST:
    Grep(pattern="test_webhook_router", path=<cwd>/tests/integration/connectors, glob="*.py")
        → present  (cross-domain: exercises both PAYMENT and MANDATE families + tampered sig)"""


# ---------------------------------------------------------------------------
# Compose surface exclusion notice
# ---------------------------------------------------------------------------

_COMPOSE_SURFACE_NOTICE = """\
╔══════════════════════════════════════════════════════════════════════╗
║ GRACE-OWNED COMPOSE SURFACE — DO NOT WRITE THESE FILES               ║
╚══════════════════════════════════════════════════════════════════════╝

Grace generates the following files deterministically after you exit. You must
NOT write them; Grace will overwrite them unconditionally anyway:

  connector.py (root)   — class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions)
  webhooks.py  (root)   — build_webhook_handlers(config) -> WebhookHandlers
                          (assembles verify, _classify, _parse_payment_webhook,
                           _parse_mandate_webhook)
  __init__.py  (root)   — requires_lens + ConnectorFactory.register + register_webhook

The cross-domain _classify(raw: bytes) -> WebhookFamily discriminator is also
part of Grace's compose surface — write only the per-domain domain parsers
(_parse_payment_webhook / _parse_mandate_webhook) in your domain webhooks.py.

Your per-domain webhook parsers are:
  orders/webhooks.py        →  _parse_payment_webhook(raw: bytes) -> PaymentWebhookEvent
  subscriptions/webhooks.py →  _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent

The composed surface calls build_webhook_handlers which wires these parsers together.
Grace also owns the final registration: ConnectorFactory.register_webhook("<psp>",
build_webhook_handlers). Do NOT duplicate that call anywhere in your output."""

# ---------------------------------------------------------------------------
# Core-creation notice (incremental vs first-creation)
# ---------------------------------------------------------------------------

_CORE_CREATION_NOTICE = """\
╔══════════════════════════════════════════════════════════════════════╗
║ CORE/ — FIRST CREATION vs INCREMENTAL                                ║
╚══════════════════════════════════════════════════════════════════════╝

  • First creation (--domain all or brand-new PSP): create core/ with all four
    files: core/base.py, core/auth.py, core/status.py, core/models.py.

  • Incremental single-domain run (e.g. --domain subscriptions on an existing
    package): core/ already exists — do NOT modify it. Only write the files
    for the requested domain listed in "Target package layout" above."""

# ---------------------------------------------------------------------------
# Locked surface block
# ---------------------------------------------------------------------------

_LOCKED_SURFACE = """\
╔══════════════════════════════════════════════════════════════════════╗
║ LOCKED SURFACE — DO NOT DEVIATE                                       ║
╚══════════════════════════════════════════════════════════════════════╝

These are the most common ways a generation can go wrong. Read them BEFORE
reading the rulebook, then re-check against this list before you finish.

1. CLASS NAMES AND HIERARCHY:
   ✓ _<Psp>Base(Connector)            — in core/base.py
   ✓ <Psp>Orders(_<Psp>Base, PaymentsConnector)     — in orders/connector.py
   ✓ <Psp>Subscriptions(_<Psp>Base, MandateConnector) — in subscriptions/connector.py
   ✗ Never subclass bare Connector for a domain mixin — only _<Psp>Base does that.
   ✗ MandatesConnector does not exist — the import is `MandateConnector` (singular).

2. IMPORTS come from these exact module paths:
{imports_block}
     from lens.connector import Connector
     from lens.webhook import WebhookHandlers, WebhookFamily
     from lens.factory import ConnectorFactory, ConnectorConfig
     from lens.common import Maskable, ConnectorError, ConnectorErrorReason
   ✗ Do NOT import from `lens.connector_abc`, `lens.types`, `lens.models`, etc.
   ✗ Do NOT import a `Money` type — the locked money type is `Amount`.

3. EVERY FLOW METHOD IS `async def`. Use the shared `self._client` (httpx.AsyncClient).
   ✓ `async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:`
   ✗ `def create_order(self, request): ...`
   ✗ Never instantiate a new httpx.AsyncClient inside a flow method or domain mixin.

4. INTROSPECTION METHODS on MandateConnector are PLAIN `def`, NOT `@property`, NOT `async def`:
   ✓ `def supported_mandate_rails(self) -> set[MandateRail]:`
   ✗ `@property` on introspection methods — the ABC does not stack @abstractmethod + @property.
   The four introspection methods are: supported_mandate_rails, supports_pause,
   supported_intervals, max_mandate_amount(rail: MandateRail).

5. DOMAIN TYPES use the exact field names from domain_types.md:
   - `request.amount.minor_units: int`             (NOT `.value`, NOT `.amount`)
   - `request.amount.currency: Currency`
   - `request.customer_id: str | None`
   - `request.idempotency_key: str | None`
   - `request.merchant_id: str`
   - `request.return_url: HttpUrl`                 (required for create_order)
   - `request.order_id: str`

   Response fields are locked (no invented extras):
   - CreateOrderResponse:     psp_order_id, payment_link, status, expires_at
   - SyncPaymentResponse:     psp_order_id, status, paid_amount (int), attempts
   - RefundResponse:          psp_refund_id, status, refunded_amount (int)
   - SyncRefundResponse:      psp_refund_id, status, refunded_amount (int), failure_reason
   - PaymentAttempt:          psp_payment_id, status, method_used, amount (Amount), failure_code,
                              failure_reason, attempted_at (required, non-optional), raw
   - CreateSubscriptionResponse: psp_subscription_id, psp_mandate_id, status, payment_link
   - SyncSubscriptionResponse:   psp_subscription_id, psp_mandate_id, status, mandate_status,
                                 next_debit_at

6. WEBHOOK SIGNATURE FAILURE raises a typed error:
     raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)
   ✗ `raise ValueError("bad signature")` will score 0 on error_handling.

7. AUTHENTICATION: credentials typed `Maskable[str]` in core/auth.py. Read with `.expose()`
   only inside the HTTP call (never log the result).
   ✗ Do NOT define a <Psp>Config dataclass — the config type is `lens.factory.ConnectorConfig`.

8. STATUS ENUMS are LOCKED — you may NOT add new values:
   - PaymentAttemptStatus = PENDING | SUCCESS | FAILED
   - RefundStatus         = PENDING | SUCCESS | FAILED
   - OrderStatus          = CREATED | PAID | PARTIALLY_REFUNDED | REFUNDED | EXPIRED | FAILED
   - MandateStatus        = ACTIVE | PAUSED | CANCELLED | EXPIRED | PENDING
   Map unknown PSP terms via status_map.py, never add new enum values.

9. FAILURE CODES come from this exact list (PaymentFailureCode enum):
   USER_DROPPED, USER_CANCELLED, CARD_DECLINED, INSUFFICIENT_FUNDS,
   AUTHENTICATION_FAILED, FRAUD_BLOCKED, FRAUD_REVIEW_PENDING,
   INVALID_INSTRUMENT, PSP_ERROR, NETWORK_ERROR, UNKNOWN.

10. MARKER BLOCK at the very top of each .py file is the only doc-header.
    Grace writes the marker for you if you forget; do NOT also write your own
    `# Code generated by ... DO NOT EDIT` comment.

11. HTTP CLIENT lifecycle:
    - Build `httpx.AsyncClient(...)` in `_<Psp>Base.__init__`. Owned by the base.
    - Close it in `async def close(self) -> None: await self._client.aclose()`.
    - Tests inject a mock via `httpx.MockTransport`."""


# ---------------------------------------------------------------------------
# Post-generation self-check block (assembled domain-conditionally)
# ---------------------------------------------------------------------------

_POST_CHECK_TYPING = """\
  MODERN TYPING — deprecated aliases only:
    Grep(pattern="\\bOptional\\b", path=<cwd>, glob="*.py")
        → ZERO matches
        ✗ `from typing import Optional`  — banned. Use `X | None` instead.
        ✓ `from typing import Callable`  — Callable is allowed (lens itself imports it).
    Grep(pattern="\\bDict\\b|\\bList\\b|\\bSet\\b|\\bTuple\\b|\\bFrozenSet\\b|\\bType\\b", path=<cwd>, glob="*.py")
        → ZERO matches (these typing aliases are deprecated)
    These are ALLOWED and should be used when needed:
        Callable, Mapping, Any, Literal, Iterable (from typing)
        dict, list, set, tuple, frozenset (built-in generics, Python 3.10+)

  If ANY check above has a non-empty match (when it should be ZERO) or a
  missing match (when it should be present), fix it before writing the
  final file out."""


# ---------------------------------------------------------------------------
# Full prompt template
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """\
You are generating a Python PSP connector for the Orbit Lens (lens 0.2.0).

Target package layout (you will create these files in the current working directory):

{file_list_block}

{compose_surface_notice}

{core_creation_notice}

{locked_surface}

╔══════════════════════════════════════════════════════════════════════╗
║ CLASS COMPOSITION RULES                                               ║
╚══════════════════════════════════════════════════════════════════════╝

{class_shape_block}

╔══════════════════════════════════════════════════════════════════════╗
║ POST-GENERATION SELF-CHECK                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Before you exit, run these checks against your own output. Use the Grep
tool with `path` set to the OUTPUT DIRECTORY (a directory, not a single
file) and `glob` to filter.

{self_check_block}

{typing_check}

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
Domain scope: {domain}

Generate the package. Do not ask follow-up questions. Write the files, run
the post-generation self-check above against your own output, then exit.
"""


# ---------------------------------------------------------------------------
# build_prompt helper
# ---------------------------------------------------------------------------


def _file_list_for_domain(domain: str) -> str:
    """Return the file-list block for the given domain."""
    if domain == "orders":
        return _FILE_LIST_CORE + "\n" + _FILE_LIST_ORDERS + "\n" + _FILE_LIST_WEBHOOK_ROUTER_TEST
    if domain == "subscriptions":
        return _FILE_LIST_CORE + "\n" + _FILE_LIST_SUBSCRIPTIONS + "\n" + _FILE_LIST_WEBHOOK_ROUTER_TEST
    # "all"
    return _FILE_LIST_ALL


def _imports_for_domain(domain: str) -> str:
    """Return the import block for the given domain (indented for item 2)."""
    if domain == "orders":
        return _IMPORTS_ORDERS
    if domain == "subscriptions":
        return _IMPORTS_SUBSCRIPTIONS
    # "all"
    return _IMPORTS_ALL


def _class_shape_for_domain(domain: str) -> str:
    """Return the class-shape instruction block for the given domain."""
    if domain == "orders":
        return _CLASS_SHAPE_CORE + "\n\n" + _CLASS_SHAPE_ORDERS
    if domain == "subscriptions":
        return _CLASS_SHAPE_CORE + "\n\n" + _CLASS_SHAPE_SUBSCRIPTIONS
    # "all"
    return _CLASS_SHAPE_CORE + "\n\n" + _CLASS_SHAPE_ORDERS + "\n\n" + _CLASS_SHAPE_SUBSCRIPTIONS


def _self_check_for_domain(domain: str) -> str:
    """Return the structural self-check block for the given domain."""
    if domain == "orders":
        return _SELF_CHECK_CORE + "\n\n" + _SELF_CHECK_ORDERS
    if domain == "subscriptions":
        return _SELF_CHECK_CORE + "\n\n" + _SELF_CHECK_SUBSCRIPTIONS
    # "all"
    return _SELF_CHECK_CORE + "\n\n" + _SELF_CHECK_ORDERS + "\n\n" + _SELF_CHECK_SUBSCRIPTIONS


def build_prompt(ctx: GenerationContext) -> str:
    domain = ctx.domain or "all"

    rulebook_block = "\n".join(f"  - {p}" for p in ctx.rulebook_paths)
    if ctx.psp_docs.source_kind == "url":
        source_block = (
            f"  - URL: {ctx.psp_docs.source_uri}\n"
            f"  - Content fetched at generation time "
            f"(use the Read tool on the cached file: see CWD)."
        )
    else:
        source_block = "\n".join(f"  - {p}" for p in ctx.psp_docs.local_paths)

    locked_surface = _LOCKED_SURFACE.replace(
        "{imports_block}", _imports_for_domain(domain) + "\n"
    )

    return PROMPT_TEMPLATE.format(
        file_list_block=_file_list_for_domain(domain),
        compose_surface_notice=_COMPOSE_SURFACE_NOTICE,
        core_creation_notice=_CORE_CREATION_NOTICE,
        locked_surface=locked_surface,
        class_shape_block=_class_shape_for_domain(domain),
        self_check_block=_self_check_for_domain(domain),
        typing_check=_POST_CHECK_TYPING,
        rulebook_block=rulebook_block,
        source_block=source_block,
        target_module=ctx.target_module,
        grace_version=ctx.grace_version,
        source_version=ctx.source_version,
        lens_version_constraint=ctx.lens_version_constraint,
        domain=domain,
    )
