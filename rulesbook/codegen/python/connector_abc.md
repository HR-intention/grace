# Connector ABC (locked)

This is the locked surface from `SUBPROJECT_LENS.md` §4.2. Do not invent additional methods. Do not rename properties. Hand-edits to the surface are forbidden — if it's broken, fix it upstream in Lens.

The class you emit subclasses this ABC. All four flow methods, both webhook + close methods, and all four properties are mandatory.

```python
# lens/connector.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lens.domain_types import (
        CreateOrderRequest, CreateOrderResponse,
        SyncPaymentRequest, SyncPaymentResponse,
        RefundRequest, RefundResponse,
        SyncRefundRequest, SyncRefundResponse,
        WebhookEvent,
    )
    from lens.enums import PaymentMethod


class Connector(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...                              # e.g., "cashfree"

    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @property
    @abstractmethod
    def supported_methods(self) -> set[PaymentMethod]: ...

    @property
    @abstractmethod
    def supports_idempotency_key(self) -> bool: ...

    @abstractmethod
    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
        """Create a hosted-checkout session/order. Returns psp_order_id and payment_link."""
        ...

    @abstractmethod
    async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
        """Poll the PSP for the order's current OrderStatus and the list of
        PaymentAttempts observed under it."""
        ...

    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundResponse:
        """Initiate a refund against the successful PaymentAttempt of an order."""
        ...

    @abstractmethod
    async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
        """Poll the PSP for the refund's current status."""
        ...

    @abstractmethod
    async def handle_webhook(
        self, raw_payload: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        """Verify the signature and parse the body. The WebhookEvent carries either
        a PaymentAttempt (for payment-level events) or a RefundEvent (for refund-level).
        Raises ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED) on bad signature."""
        ...

    @abstractmethod
    async def close(self) -> None: ...
```

## Rules when implementing

1. **`name` is a `@property` returning a string literal.** It must match the registry key (`ConnectorFactory.register("<name>", <Psp>)`).
2. **`base_url` is a `@property`.** Hard-coded sandbox URL for v1; `ConnectorConfig.base_url_override` may override at runtime.
3. **`supported_methods` returns a `set[PaymentMethod]`.** Only methods the PSP supports on hosted checkout.
4. **`supports_idempotency_key` is `bool`.** True iff the PSP honors a caller-supplied key.
5. **`__init__` takes a single `ConnectorConfig`.** Build the httpx client there; close it in `close()`.
6. **Each flow method has the exact signature above.** No extra parameters; no overloads; no defaults that change the public surface.
7. **Errors:** every method that hits the network catches `httpx` errors and raises `ConnectorError(reason=...)`. Never let a raw `httpx.HTTPError` escape.
8. **`handle_webhook` raises `ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)` when the signature fails.** No exceptions to this.
