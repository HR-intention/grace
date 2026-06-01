# Connector ABCs (capability interfaces)

Lens 0.2.0 uses a **capability-interface split**. You never subclass the thin `Connector` base
directly; instead you subclass one of the concrete capability interfaces:

| Capability | Interface | Domain folder |
|---|---|---|
| Hosted-checkout payments | `PaymentsConnector` | `orders/` |
| Subscription mandates | `MandateConnector` | `subscriptions/` |

`ConnectorFactory.register(...)` rejects any class that is not a `PaymentsConnector` or
`MandateConnector` instance — a bare `Connector` subclass raises at import time.

---

## The shared base: `_<Psp>Base(Connector)`

A per-PSP **private** base class lives in `core/base.py`. It owns:

- `name` property (returns the PSP's registry key, e.g. `"<psp>"`).
- `base_url` property (sandbox URL hard-coded in v1; overridable at runtime via
  `ConnectorConfig.base_url_override`).
- `close()` — closes the ONE shared `httpx.AsyncClient`.
- `__init__(config: ConnectorConfig)` — stores `_config`, builds the single `_client`.

```python
# core/base.py
from __future__ import annotations

from lens.connector import Connector
from lens.factory import ConnectorConfig
import httpx


class _<Psp>Base(Connector):
    @property
    def name(self) -> str:
        return "<psp>"

    @property
    def base_url(self) -> str:
        return "<PSP_SANDBOX_URL>"   # hard-coded; override via config.base_url_override

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()
```

One client, owned by `_<Psp>Base`, shared by every domain mixin.

---

## Domain mixin: `<Psp>Orders(_<Psp>Base, PaymentsConnector)`

Implements the four payment flows. Lives in `orders/connector.py`.

```python
# orders/connector.py
from __future__ import annotations

from lens.payments_connector import PaymentsConnector
from lens.domain_types import (
    CreateOrderRequest, CreateOrderResponse,
    SyncPaymentRequest, SyncPaymentResponse,
    RefundRequest, RefundResponse,
    SyncRefundRequest, SyncRefundResponse,
)
from lens.enums import PaymentMethod
from <psp>.core.base import _<Psp>Base


class <Psp>Orders(_<Psp>Base, PaymentsConnector):

    @property
    def supported_methods(self) -> set[PaymentMethod]:
        return {PaymentMethod.CARD, PaymentMethod.UPI}   # PSP-specific allow-list

    @property
    def supports_idempotency_key(self) -> bool:
        return True   # or False — per PSP docs

    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse: ...
    async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse: ...
    async def refund(self, request: RefundRequest) -> RefundResponse: ...
    async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse: ...
```

`PaymentsConnector` (from `lens/payments_connector.py`) declares these signatures.
Do **not** add extra parameters or change return types.

---

## Domain mixin: `<Psp>Subscriptions(_<Psp>Base, MandateConnector)`

Implements the five lifecycle methods + four introspection methods. Lives in
`subscriptions/connector.py`.

```python
# subscriptions/connector.py
from __future__ import annotations

from lens.mandate_connector import MandateConnector
from lens.domain_types import (
    CreateSubscriptionRequest, CreateSubscriptionResponse,
    SyncSubscriptionRequest, SyncSubscriptionResponse,
    ManageMandateRequest, ManageMandateResponse,
    Amount,
)
from lens.enums import MandateIntervalType, MandateRail
from <psp>.core.base import _<Psp>Base


class <Psp>Subscriptions(_<Psp>Base, MandateConnector):

    # --- 4 introspection methods (plain def, NOT @property) ---

    def supported_mandate_rails(self) -> set[MandateRail]:
        return {MandateRail.UPI_AUTOPAY, MandateRail.CARD_EMANDATE}

    def supports_pause(self) -> bool:
        return True   # per PSP docs

    def supported_intervals(self) -> set[MandateIntervalType]:
        return {MandateIntervalType.MONTH}   # per PSP docs

    def max_mandate_amount(self, rail: MandateRail) -> Amount | None:
        return None   # unknown / PSP-defined

    # --- 5 lifecycle methods (async) ---

    async def create_subscription(
        self, request: CreateSubscriptionRequest
    ) -> CreateSubscriptionResponse: ...

    async def sync_subscription(
        self, request: SyncSubscriptionRequest
    ) -> SyncSubscriptionResponse: ...

    async def cancel_subscription(
        self, request: ManageMandateRequest
    ) -> ManageMandateResponse: ...

    async def pause_subscription(
        self, request: ManageMandateRequest
    ) -> ManageMandateResponse: ...

    async def resume_subscription(
        self, request: ManageMandateRequest
    ) -> ManageMandateResponse: ...
```

**`MandateConnector` is singular** — the class and import are `MandateConnector` (not
`MandatesConnector`). Only the *facade* is plural (`MandatesFacade`).

The four introspection methods (`supported_mandate_rails`, `supports_pause`,
`supported_intervals`, `max_mandate_amount`) are **plain methods, not `@property`**. The
ABC declares them without `@abstractmethod` + `@property` stacking. `max_mandate_amount`
takes a `rail: MandateRail` argument, which is why it cannot be a property.

---

## Grace-owned compose surface

The root `connector.py` (Grace-generated, not per-domain) composes both mixins:

```python
# connector.py  (root of the generated package)
from <psp>.orders.connector import <Psp>Orders
from <psp>.subscriptions.connector import <Psp>Subscriptions


class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions):
    """Full-capability connector. MRO resolves _<Psp>Base once (C3)."""
```

`_<Psp>Base` appears once in the MRO — Python's C3 linearization handles it automatically.
The composed class has zero leftover abstract methods; it passes `ConnectorFactory.register`.

---

## Rules when implementing

1. **`name` is a `@property` returning a string literal** matching the registry key
   (`ConnectorFactory.register("<psp>", <Psp>Connector)`).
2. **`base_url` is a `@property`.** Hard-code the sandbox URL in `_<Psp>Base`; apply
   `config.base_url_override` at `__init__` time.
3. **One `httpx.AsyncClient`, built in `_<Psp>Base.__init__`.** Never build a second client
   in a domain mixin.
4. **`__init__` takes a single `ConnectorConfig`.** Build the client there; do not call
   `.expose()` on optional credentials — defer that to call time.
5. **Each flow method has the exact ABC signature.** No extra parameters, no defaults that
   change the public surface.
6. **Errors:** every method that hits the network catches `httpx` errors and raises
   `ConnectorError(reason=...)`. Never let a raw `httpx.HTTPError` escape.
7. **Introspection methods are plain `def`, not `async def`, not `@property`.** They return
   in-memory constants; no I/O involved.
8. **Both `ConnectorFactory.register(...)` and `ConnectorFactory.register_webhook(...)` must be
   called at module scope in `__init__.py`.** Do **not** declare `requires_lens` — the connector
   version gate was removed in constitution v0.6.
9. **Authentication None-guard in `core/auth.py`** — credential optionality:
   - `config.api_key` is `Maskable[str]` — always present, safe to call `.expose()` directly.
   - `config.secret_key` is `Maskable[str] | None` — guard with `assert … is not None` or
     `if … is None: raise ConnectorError(reason=ConnectorErrorReason.AUTHENTICATION_FAILED)`
     before calling `.expose()`.
   - `config.webhook_secret` is `Maskable[str] | None` — same None-guard required before
     `.expose()` in `verify_signature`.
   Calling `.expose()` on a `None` value raises `AttributeError` at runtime and crashes
   `mypy --strict` type checking.
