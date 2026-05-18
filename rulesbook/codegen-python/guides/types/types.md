# Python type-system reference

Authoritative cross-reference between symbols the rulesbook patterns name
and what exists in `connector-service-python/connector_service/domain_types/`.

Every name in this file MUST be importable from `connector_service.domain_types`.
The contract test at `connector-service-python/tests/contract/test_types_contract.py`
fails the build if any name drifts.

## Top-level imports

All names below are re-exported from `connector_service.domain_types`:

```python
from connector_service.domain_types import (
    # Envelope
    PaymentData, WebhookEvent,
    # Flow request/response pairs
    AuthorizeRequest, AuthorizeResponse,
    PSyncRequest, PSyncResponse,
    CaptureRequest, CaptureResponse,
    VoidRequest, VoidResponse,
    RefundRequest, RefundResponse,
    RSyncRequest, RSyncResponse,
    # Composite shapes
    CustomerData, RedirectionData, PaymentMethodInput,
    # Payment-method models
    CardData, WalletData, UpiData,
    # Enums
    Flow, AttemptStatus, RefundStatus,
    Currency, Country, PaymentMethod, WalletType, UpiFlowType,
    # Money & errors & masking
    Amount,
    ConnectorError, ValidationError, AuthenticationError, UpstreamTimeoutError, ErrorResponse,
    mask_vpa, mask_card_number, mask_pan,
    # Credentials
    BaseAuth, load_creds,
)
```

## PaymentData envelope

```python
class PaymentData(BaseModel, Generic[Req, Resp]):
    flow: Flow
    request: Req                          # parameterized per flow
    response: Optional[Resp] = None       # filled by the connector's flow method
    status: Optional[AttemptStatus] = None
    idempotency_key: Optional[str] = None # auto-injected by @connector_flow if absent
    request_id: str
    connector_name: str
```

`(Req, Resp)` is parameterized differently per flow — see the table below.

## Flow request/response pairs

| Flow | Request | Response |
|---|---|---|
| Authorize | `AuthorizeRequest` (amount, payment_method, customer, return_url, capture_method, metadata) | `AuthorizeResponse` (connector_payment_id, status, redirection_data, raw_response) |
| PSync | `PSyncRequest` (connector_payment_id) | `PSyncResponse` (connector_payment_id, status, amount_received, raw_response) |
| Capture | `CaptureRequest` (connector_payment_id, amount_to_capture) | `CaptureResponse` (connector_payment_id, status, amount_captured, raw_response) |
| Void | `VoidRequest` (connector_payment_id, cancellation_reason) | `VoidResponse` (connector_payment_id, status, raw_response) |
| Refund | `RefundRequest` (connector_payment_id, refund_amount, refund_reason) | `RefundResponse` (connector_refund_id, status, refund_amount, raw_response) |
| RSync | `RSyncRequest` (connector_refund_id) | `RSyncResponse` (connector_refund_id, status, raw_response) |

`IncomingWebhook` does not use this pattern — see [`../patterns/pattern_IncomingWebhook_flow.md`](../patterns/pattern_IncomingWebhook_flow.md).

## Payment-method models

```python
class CardData(BaseModel):
    card_number: str
    card_exp_month: str
    card_exp_year: str
    card_holder_name: str
    card_cvc: str
    card_issuer: Optional[str] = None

class WalletData(BaseModel):
    wallet_type: WalletType  # APPLE_PAY | GOOGLE_PAY | PAYPAL | SAMSUNG_PAY | PAYTM | PHONEPE
    token: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UpiData(BaseModel):
    upi_flow: UpiFlowType  # COLLECT | INTENT
    vpa: Optional[str] = None  # required for Collect; optional for Intent
```

## BaseConnector + decorator + registry

These come from `connector_service.connectors._base` and `connector_service.connectors._registry`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector

class {Connector}(BaseConnector):
    name = "{connector}"
    base_url = "{base_url}"
    AuthCls = {Connector}Auth  # subclass of BaseAuth

    @connector_flow(flow=Flow.AUTHORIZE)
    async def authorize(self, data: PaymentData[AuthorizeRequest, AuthorizeResponse]) -> PaymentData[AuthorizeRequest, AuthorizeResponse]:
        # body: transformer → http call → response transformer → status mapping
        ...

# Register at module load:
register_connector("{connector}", {Connector})
```

The `@connector_flow` decorator handles cross-cutting concerns automatically:
- Generates a UUID4 idempotency key if `data.idempotency_key` is None.
- Logs `request_id`, `connector_name`, `flow`, `idempotency_key`, `latency_ms`.
- Translates `httpx.TimeoutException` → `UpstreamTimeoutError`, `httpx.HTTPStatusError` → `ConnectorError(retryable=status>=500)`, `pydantic.ValidationError` → `ValidationError`.

You do NOT need to repeat these in the body.

## Authentication

`BaseAuth` is the minimum:

```python
class BaseAuth(BaseModel):
    api_key: str
    webhook_secret: Optional[str] = None  # required if the connector implements IncomingWebhook
```

Subclass per connector if the PSP needs more fields:

```python
class RazorpayAuth(BaseAuth):
    api_key: str
    api_secret: str
    webhook_secret: str  # required (no default — Razorpay always uses webhooks)
```

## Errors

```python
class ConnectorError(Exception):
    message: str
    retryable: bool                       # 5xx → True, 4xx → False (default)
    connector_status_code: Optional[str]

class ValidationError(ConnectorError): ...           # body / payload validation
class AuthenticationError(ConnectorError): ...        # 401/403/signature mismatch
class UpstreamTimeoutError(ConnectorError): ...       # retryable=True by default
```

## Masking

```python
mask_vpa("alice@oksbi")           # → "al****@oksbi"
mask_card_number("4242424242424242")  # → "424242******4242"
mask_pan("ABCDE1234F")             # → "ABC****34F"
```

The structlog `mask_processor` auto-redacts these field names: `pan`, `card_number`, `card_pan`, `cvv`, `cvc`, `card_cvc`, `vpa`, `indian_pan`. Log them as field-name keys to get free masking.

## Validity guarantees

This file is enforced by `tests/contract/test_types_contract.py` in `connector-service-python`. If a name listed here is missing from `connector_service.domain_types`, the contract test fails and Plan D's codegen is blocked.
