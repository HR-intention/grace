# File layout (mandatory)

Verbatim from `SUBPROJECT_GRACE_CODEGEN.md` §3.2. Grace's rubric verifies these files exist;
missing files cost rubric points.

```
connectors/<psp>/
  __init__.py            # requires_lens = "^0.2"
                         # ConnectorFactory.register("<psp>", <Psp>Connector)
                         # ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
  connector.py           # class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions): ...
  webhooks.py            # build_webhook_handlers(config) -> WebhookHandlers
  core/
    base.py              # _<Psp>Base(Connector): name, base_url, close, __init__ + _client
    auth.py              # build_auth_headers + verify_signature (shared HMAC, family-agnostic)
    status.py            # failure free-text -> (PaymentFailureCode, FailureClass)
    models.py            # shared wire models (webhook envelope, error body)
  orders/
    connector.py         # class <Psp>Orders(_<Psp>Base, PaymentsConnector): 4 flows + 2 props
    models.py            # payment wire models
    status_map.py        # PSP payment status -> (PaymentAttemptStatus, PaymentFailureCode)
    webhooks.py          # _parse_payment_webhook(bytes) -> PaymentWebhookEvent
  subscriptions/
    connector.py         # class <Psp>Subscriptions(_<Psp>Base, MandateConnector): 5 lifecycle + 4 introspection
    models.py            # subscription / plan / mandate wire models
    status_map.py        # subscription_status -> MandateStatus; event -> WebhookEventType
    webhooks.py          # _parse_mandate_webhook(bytes) -> MandateWebhookEvent
```

---

## What goes in each file

```
__init__.py          — Module scope: declare requires_lens = "^0.2".
                       At the bottom: import and register both:
                         ConnectorFactory.register("<psp>", <Psp>Connector)
                         ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)

connector.py (root)  — class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions).
                       Grace-owned compose surface. No methods defined here — all
                       behaviour is inherited. MRO resolves _<Psp>Base once via C3.

webhooks.py (root)   — build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers.
                       Assembles verify (closes over config), _classify, and the two
                       domain parsers into a WebhookHandlers frozen dataclass.
                       Also defines _classify(raw: bytes) -> WebhookFamily.

core/base.py         — _<Psp>Base(Connector). Implements name, base_url, close, __init__.
                       Builds and owns the ONE httpx.AsyncClient. Stores _config.
                       This is the identity + lifecycle root for all domain mixins.

core/auth.py         — Signing helpers. Credentials typed Maskable[str]. Functions:
                         build_auth_headers(config: ConnectorConfig) -> dict[str, str]
                         verify_signature(config, raw_payload, headers) -> bool
                       No global state. verify_signature uses hmac.compare_digest.

core/status.py       — Shared failure-reason → (PaymentFailureCode, FailureClass) lookup.
                       Ordered substring-match list _FAILURE_SUBSTRINGS; function
                       map_failure_reason(text: str | None) -> tuple[...].
                       Imports FAILURE_CLASS from lens.enums (never redeclares it).

core/models.py       — Shared wire models used by both domains: webhook envelope,
                       error-response body. extra="forbid"; frozen=True on request
                       shapes, frozen=False on response shapes.

orders/connector.py  — class <Psp>Orders(_<Psp>Base, PaymentsConnector).
                       Implements supported_methods, supports_idempotency_key (both
                       @property), and the four async flows: create_order, sync_payment,
                       refund, sync_refund.

orders/models.py     — Payment wire models (Pydantic). extra="forbid"; frozen=True on
                       request bodies, frozen=False on response bodies.

orders/status_map.py — PSP payment status string -> (PaymentAttemptStatus, PaymentFailureCode).
                       Single dict STATUS_MAP; function map_payment_status(s: str) -> tuple[...].
                       Falls back to (FAILED, UNKNOWN) + structlog.warning on unknown values.

orders/webhooks.py   — _parse_payment_webhook(raw: bytes) -> PaymentWebhookEvent.
                       Parses already-verified bytes into the domain event. Branches on
                       payment vs refund vs order-expired; returns PaymentWebhookEvent.

subscriptions/connector.py — class <Psp>Subscriptions(_<Psp>Base, MandateConnector).
                       Implements 4 introspection methods (plain def, not @property):
                         supported_mandate_rails() -> set[MandateRail]
                         supports_pause() -> bool
                         supported_intervals() -> set[MandateIntervalType]
                         max_mandate_amount(rail: MandateRail) -> Amount | None
                       And 5 async lifecycle methods:
                         create_subscription, sync_subscription,
                         cancel_subscription, pause_subscription, resume_subscription.

subscriptions/models.py    — Subscription / plan / mandate wire models (Pydantic).

subscriptions/status_map.py — PSP subscription_status -> MandateStatus;
                       PSP event-type string -> WebhookEventType.
                       Two dicts + two map_* functions; unknown values log a warning
                       and return the documented fallback.

subscriptions/webhooks.py  — _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent.
                       Parses already-verified bytes into the mandate domain event.
```

---

## Tests layout

Write tests into the **package-local `tests/` directory**. Grace's pipeline relocates
`<output_dir>/tests/` to the consumer's configured `paths.tests_dir/<psp>/` after
generation — do NOT write that final path yourself. Writing
`tests/integration/connectors/<psp>/…` doubles the path and pytest collects 0 tests.

```
tests/
  test_create_order.py
  test_sync_payment.py
  test_refund.py
  test_sync_refund.py
  test_create_subscription.py
  test_sync_subscription.py
  test_manage_mandate.py       # covers cancel_subscription, pause_subscription, resume_subscription
  test_pause_subscription.py
  test_resume_subscription.py
  test_mandate_webhook.py
  test_webhook_router.py       # cross-domain: one WebhookRouter dispatching both families
```

The cross-domain `test_webhook_router.py` exercises the full `build_webhook_handlers →
WebhookRouter.handle` path for both `PAYMENT` and `MANDATE` families, including the
tampered-signature → `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` case.

---

## Optional / additive files

Extra helper modules (e.g., a custom token-refresh helper) are allowed but do not earn rubric
points. They must still carry the §4 marker.

---

## Notes

- `tests/__init__.py` is optional but harmless.
- Use these canonical import paths:
  ```python
  from lens.connector import Connector
  from lens.payments_connector import PaymentsConnector
  from lens.mandate_connector import MandateConnector
  from lens.webhook import WebhookFamily, WebhookHandlers, WebhookRouter
  from lens.factory import ConnectorConfig, ConnectorFactory
  from lens.domain_types import ...
  from lens.enums import ...
  from lens.common import Maskable, ConnectorError, ConnectorErrorReason
  ```
- `MandateConnector` is singular; `MandatesConnector` does not exist (only the facade is plural).
- `requires_lens = "^0.2"` (not `"^0.1"`). The factory checks this at registration time.
