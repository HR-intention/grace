# Common pitfalls (read first, re-read at the end)

Every deviation listed here costs rubric points. The fixes are concrete and unambiguous — there is no PSP for which the *wrong* version is correct.

## 1. Class naming

| ✗ Wrong | ✓ Right |
|---|---|
| `class CashfreeConnector(Connector)` | `class Cashfree(Connector)` |
| `class CashfreeClient(Connector)` | `class Cashfree(Connector)` |
| `class CashfreePaymentConnector(Connector)` | `class Cashfree(Connector)` |

The class name is the PSP name in PascalCase, **no suffix**. The registry key (the first arg to `ConnectorFactory.register`) is the same string in lowercase. The rubric's public-surface scorer does a case-insensitive name match against the PSP name — `connector.py: no class named <psp>` is a 4-point dock per missing element.

## 2. Import paths

| ✗ Wrong | ✓ Right |
|---|---|
| `from lens.connector_abc import Connector` | `from lens.connector import Connector` |
| `from lens.types import ...` | `from lens.domain_types import ...` |
| `from lens.models import ...` | `from lens.domain_types import ...` |
| `from lens.errors import ConnectorError` | `from lens.common import ConnectorError` |
| `from lens.domain_types import Money` | `from lens.domain_types import Amount` |

There is **no `Money` type**. Money is represented by `Amount(minor_units: int, currency: Currency)` — int minor units only (ground rule 10).

## 3. Sync vs async

| ✗ Wrong | ✓ Right |
|---|---|
| `def create_order(self, request): ...` | `async def create_order(self, request): ...` |
| `httpx.Client(...)` | `httpx.AsyncClient(...)` |
| `self._client.post(...)` | `await self._client.post(...)` |
| (in tests) `def test_create_order():` | `async def test_create_order():` |

Every public method on `Connector` is `async def`. Ground rule 3. Tests use `pytest-asyncio` with `asyncio_mode = "auto"`, so a top-level `async def test_*` runs as a coroutine.

## 4. Request field access

The locked `CreateOrderRequest` (and siblings) have a **flat** field set inherited from `RequestCommon`. There is no nested `customer` object.

| ✗ Wrong | ✓ Right |
|---|---|
| `request.customer.id` | `request.customer_id` |
| `request.customer.email` | (not on the domain request — PSPs that need email read it from `metadata` or just omit) |
| `request.amount.value` | `request.amount.minor_units` |
| `float(request.amount.value)` | `Decimal(request.amount.minor_units) / 100` (only inside the wire-level builder, never crossing back out) |

If the PSP requires a customer email/phone/name and the domain request doesn't carry it, **pass a placeholder or omit the field** — do NOT invent additional request fields. Orbit owns the customer record.

## 5. `__init__.py` self-registration

The generated `__init__.py` must declare the Lens version constraint **and** register the class with the factory:

```python
# CORRECT:
requires_lens = "^0.1"

from .connector import Cashfree
from lens.factory import ConnectorFactory
ConnectorFactory.register("cashfree", Cashfree)
```

```python
# WRONG — common mistake: only an __all__ export, no registration:
from .connector import Cashfree
__all__ = ["Cashfree"]
```

The rubric's public-surface scorer greps for both literal strings; the second style scores 8/20 instead of 20/20.

## 6. Credentials in `auth.py`

```python
# CORRECT:
from lens.common import Maskable
from lens.factory import ConnectorConfig

def build_auth_headers(config: ConnectorConfig) -> dict[str, str]:
    return {
        "x-client-id": config.api_key.expose(),
        "x-client-secret": config.secret_key.expose() if config.secret_key else "",
    }
```

```python
# WRONG — bare strings, no Maskable, custom config dataclass:
@dataclass(frozen=True)
class CashfreeConfig:
    client_id: str            # ← no Maskable
    client_secret: str        # ← no Maskable
```

**Do not define a `<Psp>Config` dataclass.** The credentials shape is `lens.factory.ConnectorConfig` (api_key, secret_key, webhook_secret, base_url_override, additional). Auth helpers take that and produce headers.

## 7. Webhook signature failure

```python
# CORRECT:
from lens.common import ConnectorError
from lens.enums import ConnectorErrorReason

async def handle_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    if not verify_signature(self._config, raw_payload, headers):
        raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)
    ...
```

```python
# WRONG — bare exception, untyped, undiscoverable by callers:
if not verify_signature(...):
    raise ValueError("signature verification failed")
```

The rubric's error-handling scorer greps for `WEBHOOK_SIGNATURE_FAILED` and for `ConnectorError`. Both must appear in `connector.py`.

## 8. Status enum values (LOCKED — only these exist)

`PaymentAttemptStatus`: `PENDING`, `SUCCESS`, `FAILED` — three values, **nothing else**.

| ✗ Invented values | ✓ Locked equivalent |
|---|---|
| `PaymentAttemptStatus.CAPTURED` | `PaymentAttemptStatus.SUCCESS` |
| `PaymentAttemptStatus.AUTHORIZED` | `PaymentAttemptStatus.SUCCESS` (for hosted checkout — capture happens at the PSP) |
| `PaymentAttemptStatus.CANCELLED` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.USER_CANCELLED` |
| `PaymentAttemptStatus.VOID` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.USER_CANCELLED` (or `UNKNOWN`) |
| `PaymentAttemptStatus.REJECTED` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.CARD_DECLINED` |

`PaymentFailureCode` values (the only ones that exist):
`USER_DROPPED`, `USER_CANCELLED`, `CARD_DECLINED`, `INSUFFICIENT_FUNDS`, `AUTHENTICATION_FAILED`, `FRAUD_BLOCKED`, `FRAUD_REVIEW_PENDING`, `INVALID_INSTRUMENT`, `PSP_ERROR`, `NETWORK_ERROR`, `UNKNOWN`.

| ✗ Invented codes | ✓ Locked equivalent |
|---|---|
| `PAYMENT_DECLINED` | `CARD_DECLINED` |
| `CUSTOMER_CANCELLED` | `USER_CANCELLED` |
| `EXPIRED_CARD` | `INVALID_INSTRUMENT` (or `CARD_DECLINED` per PSP signal) |
| `TIMEOUT` | `NETWORK_ERROR` |
| `INVALID_CARD` | `INVALID_INSTRUMENT` |

If you find yourself wanting a value that's not here, fall back to `UNKNOWN` and capture the PSP-original term in `failure_reason: str`.

## 9. Marker block duplication

Grace prepends the constitution §4 marker to every emitted file. **Do not also write a second marker** like `# Code generated by grace ... DO NOT EDIT.\n# source: lens.connectors.cashfree`. That ends up duplicated and confusing.

The first thing after the marker should be `from __future__ import annotations`, then the module docstring (optional), then imports.

## 10. httpx client

```python
# CORRECT — async client, owned by Connector, closed in close():
def __init__(self, config: ConnectorConfig):
    self._config = config
    self._client = httpx.AsyncClient(
        base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
        timeout=30.0,
    )

async def close(self) -> None:
    await self._client.aclose()
```

```python
# WRONG — sync client + lazy build inside flow methods:
def __init__(self, config):
    self._config = config

def _client(self):
    return httpx.Client(...)   # rebuilt every call, sync, never closed
```

## Final self-check

Before exiting, grep your output for each of these and confirm:

```
grep -E '^class [A-Z][a-z]+\(Connector\)' connector.py        # exactly 1 match
grep 'from lens.connector import Connector' connector.py       # present
grep 'ConnectorFactory.register' __init__.py                   # present
grep 'requires_lens' __init__.py                                # present
grep -c 'async def' connector.py                                # >= 6
grep 'Maskable' auth.py                                         # >= 1
grep 'WEBHOOK_SIGNATURE_FAILED' connector.py                    # >= 1
grep -E 'Money|float\(' connector.py models.py                  # 0 matches
grep -E 'PaymentAttemptStatus\.(CAPTURED|AUTHORIZED|CANCELLED|VOID|REJECTED)' status_map.py   # 0 matches
grep -E 'PaymentFailureCode\.(PAYMENT_DECLINED|CUSTOMER_CANCELLED|EXPIRED_CARD|TIMEOUT)' status_map.py  # 0 matches
```

If any of these don't match the expected count, fix before writing the file out.
