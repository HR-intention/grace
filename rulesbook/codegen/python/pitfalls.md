# Common pitfalls (read first, re-read at the end)

Every deviation listed here costs rubric points. The fixes are concrete and unambiguous.

---

## 1. Class naming

The **domain mixin** classes follow this naming:

| ✗ Wrong | ✓ Right |
|---|---|
| `class <Psp>Connector(Connector)` | `class _<Psp>Base(Connector)` in `core/base.py` |
| `class <Psp>PaymentsConnector(...)` | `class <Psp>Orders(_<Psp>Base, PaymentsConnector)` |
| `class <Psp>MandatesConnector(...)` | `class <Psp>Subscriptions(_<Psp>Base, MandateConnector)` |

The composed class is `<Psp>Connector` (e.g. `CashfreeConnector`) and lives in root
`connector.py`. The shared base is prefixed with `_` to signal it is not a public type.

`MandateConnector` is **singular** — there is no `MandatesConnector` class in lens.

## 1b. Capability interfaces — never bare `Connector`

`ConnectorFactory.register(...)` rejects any class that is not `isinstance` of
`PaymentsConnector` or `MandateConnector`. A class that only inherits from `Connector` raises
at import time:

```
ConnectorError(reason=INVALID_REQUEST):
  <Psp>Connector must implement a capability interface
  (PaymentsConnector / MandateConnector), not bare Connector
```

and your tests can't even collect.

```python
# WRONG — bare Connector, no capability interface:
class CashfreeConnector(Connector):
    ...
```

```python
# CORRECT — composed class inherits capability interfaces via domain mixins:
class CashfreeConnector(CashfreeOrders, CashfreeSubscriptions):
    """Full-capability connector."""
    # no methods needed — all behaviour is inherited
```

## 2. Import paths

| ✗ Wrong | ✓ Right |
|---|---|
| `from lens.connector_abc import Connector` | `from lens.connector import Connector` |
| `from lens.types import ...` | `from lens.domain_types import ...` |
| `from lens.errors import ConnectorError` | `from lens.common import ConnectorError` |
| `from lens.domain_types import Money` | `from lens.domain_types import Amount` |
| `from lens.mandate_connectors import MandateConnector` | `from lens.mandate_connector import MandateConnector` |
| `from lens.domain_types.mandates import MandateWebhookEvent` | `from lens.domain_types import MandateWebhookEvent` |

There is **no `Money` type**. There is **no `MandatesConnector`**. The mandate connector is
`lens.mandate_connector.MandateConnector` (singular).

## 3. Sync vs async

| ✗ Wrong | ✓ Right |
|---|---|
| `def create_order(self, ...)` | `async def create_order(self, ...)` |
| `httpx.Client(...)` | `httpx.AsyncClient(...)` |
| `def supported_mandate_rails(self):` as `async def` | `def supported_mandate_rails(self):` — plain sync def |
| (in tests) `def test_*():` | `async def test_*() -> None:` |

Lifecycle methods (`create_subscription`, `sync_subscription`, `cancel_subscription`,
`pause_subscription`, `resume_subscription`) are `async def`. Introspection methods
(`supported_mandate_rails`, `supports_pause`, `supported_intervals`, `max_mandate_amount`)
are **plain `def`** — they return in-memory constants.

## 4. Request field access

`MandateRequestCommon` has **no `order_id`** — mandates are not orders.

| ✗ Wrong | ✓ Right |
|---|---|
| `request.order_id` on a mandate request | `request.psp_mandate_ref` |
| `request.customer.email` | `request.customer_contact.email` |
| `request.amount.value` | `request.amount.minor_units` |

`CreateSubscriptionRequest` carries `idempotency_key` directly (not inside a nested bag).

## 4b. `psp_order_id` does NOT exist on `RefundRequest` or `SyncRefundRequest`

Only `SyncPaymentRequest` has `psp_order_id`. `RefundRequest` and `SyncRefundRequest` do not.

| ✗ Wrong | ✓ Right |
|---|---|
| `request.psp_order_id` in `refund` flow | `request.order_id` |
| `request.psp_order_id` in `sync_refund` flow | `request.order_id` |
| `request.amount` on `RefundRequest` | `request.amount_to_refund` (int\|None) |
| `request.refund_id` on `SyncRefundRequest` | `request.psp_refund_id` |

PSPs that scope refund endpoints to an order (e.g. `POST /orders/{id}/refunds`,
`GET /orders/{id}/refunds/{refund_id}`) must use **`request.order_id`** — the merchant
order id Orbit stored at create-order time. Accessing `request.psp_order_id` on these
types causes `AttributeError` at runtime (the field does not exist; pydantic's
`extra="forbid"` would also block construction with it).

Full field inventory for reference:

```
CreateOrderRequest:    merchant_id, order_id, customer_id, idempotency_key,
                       amount, return_url, allowed_methods, expires_at, metadata
SyncPaymentRequest:    merchant_id, order_id, customer_id, idempotency_key, psp_order_id
RefundRequest:         merchant_id, order_id, customer_id, idempotency_key,
                       psp_payment_id, refund_id, amount_to_refund, reason
SyncRefundRequest:     merchant_id, order_id, customer_id, idempotency_key, psp_refund_id
```

## 4c. `refunded_amount` and `paid_amount` are int minor-units, NOT `Amount`

`SyncPaymentResponse.paid_amount` and `RefundResponse.refunded_amount` /
`SyncRefundResponse.refunded_amount` are plain `int` (minor units, e.g. paise), not `Amount`.

| ✗ Wrong | ✓ Right |
|---|---|
| `paid_amount=Amount(minor_units=…, currency=…)` | `paid_amount=1234` (int) |
| `refunded_amount=Amount(minor_units=…, currency=…)` | `refunded_amount=1234` (int) |

`PaymentAttempt.amount` is `Amount | None` — that is the only Amount on the response side.

## 4a. Introspection methods are plain `def`, not `@property`

The `MandateConnector` ABC declares:

```python
@abstractmethod
def supported_mandate_rails(self) -> set[MandateRail]: ...

@abstractmethod
def supports_pause(self) -> bool: ...

@abstractmethod
def supported_intervals(self) -> set[MandateIntervalType]: ...

@abstractmethod
def max_mandate_amount(self, rail: MandateRail) -> Amount | None: ...
```

None of these is a `@property`. Decorating them with `@property` in your implementation
violates LSP: the ABC's `@abstractmethod` without `@property` means plain method. Callers
do `connector.supported_mandate_rails()` with parens — not `connector.supported_mandate_rails`.

## 5. `__init__.py` — both registrations required

```python
# CORRECT — both calls mandatory:
from <psp>.connector import <Psp>Connector
from <psp>.webhooks import build_webhook_handlers
from lens.factory import ConnectorFactory

ConnectorFactory.register("<psp>", <Psp>Connector)
ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
```

```python
# WRONG — missing register_webhook:
ConnectorFactory.register("<psp>", <Psp>Connector)
# no register_webhook → rubric docks public-surface points
```

Do **not** declare `requires_lens` — the connector version gate was removed in constitution
v0.6 (connectors ship bundled inside the `lens` wheel, so nothing reads it).

## 5b. `__init__` must NOT touch credentials — defer to HTTP call time

`ConnectorConfig` optional fields may be `None` at register time (the factory calls
`connector_cls(stub_config)` to verify the `name` property). Calling `.expose()` on
an optional credential in `__init__` crashes with `AttributeError: 'NoneType'`.

```python
# WRONG — .expose() in __init__ crashes on stub_config:
def __init__(self, config: ConnectorConfig) -> None:
    self._config = config
    self._client = httpx.AsyncClient(
        headers={"x-api-key": config.api_key.expose()}   # ← crashes on stub
    )
```

```python
# CORRECT — defer credential access to call sites (auth.py helpers):
def __init__(self, config: ConnectorConfig) -> None:
    self._config = config
    self._client = build_http_client(
        base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
        connector_name=self.name,
        timeout=30.0,
    )
```

## 5c. `secret_key` and `webhook_secret` are `Maskable[str] | None` — guard before `.expose()`

Only `config.api_key` is guaranteed non-None (`Maskable[str]`). Both `config.secret_key` and
`config.webhook_secret` are `Maskable[str] | None`. Calling `.expose()` on a `None` value
raises `AttributeError` at runtime.

```python
# WRONG — AttributeError if secret_key is None:
headers["x-client-secret"] = self._config.secret_key.expose()
```

```python
# CORRECT — assert or raise before calling .expose():
assert self._config.secret_key is not None, "secret_key required for this PSP"
headers["x-client-secret"] = self._config.secret_key.expose()

# Alternative — raise a typed ConnectorError:
if self._config.webhook_secret is None:
    raise ConnectorError(reason=ConnectorErrorReason.AUTHENTICATION_FAILED)
secret = self._config.webhook_secret.expose()
```

This None-guard must appear in `core/auth.py` before every call to `.expose()` on an optional
credential. The post-generation self-check grep for `.expose()` in `core/auth.py` must find
only guarded call sites.

## 6. Modern typing — deprecated aliases BANNED

The rubric type-correctness dimension requires modern Python 3.11 typing throughout.

| ✗ Banned (deprecated `typing` aliases) | ✓ Modern built-in / `typing` |
|---|---|
| `Dict[str, str]` | `dict[str, str]` |
| `List[str]` | `list[str]` |
| `Optional[str]` | `str \| None` |
| `Set[PaymentMethod]` | `set[PaymentMethod]` |
| `Tuple[str, int]` | `tuple[str, int]` |

**Allowed** from `typing`: `Callable`, `Mapping`, `Any`, `Literal`, `TypeVar`, `Generic`.

`from __future__ import annotations` at the top of every file enables lazy evaluation of
annotations and prevents accidental breakage on forward references.

## 7. One shared httpx client

```python
# CORRECT — one client in _<Psp>Base, shared by all domain mixins:
class _<Psp>Base(Connector):
    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client = build_http_client(
            base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
            connector_name=self.name,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()
```

```python
# WRONG — each domain mixin builds its own client:
class <Psp>Orders(_<Psp>Base, PaymentsConnector):
    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._client = httpx.AsyncClient(...)   # ← second client, leaks connections
```

One client, owned by `_<Psp>Base`, never overridden by a domain mixin.

## 8. `FAILURE_CLASS` — never redeclare, never branch on

```python
# CORRECT — import and reference only:
from lens.enums import FAILURE_CLASS, PaymentFailureCode

# In core/status.py — just import; connector sets failure_code only:
failure_code, _ = map_failure_reason(psp_reason_text)
outcome = MandateDebitOutcome(
    ...
    failure_code=failure_code,
    ...
)
```

```python
# WRONG — redeclaring the mapping:
_MY_FAILURE_CLASS: dict[PaymentFailureCode, str] = {
    PaymentFailureCode.CARD_DECLINED: "TERMINAL",
    ...
}
```

```python
# WRONG — branching on FailureClass inside the connector:
if FAILURE_CLASS.get(code) == FailureClass.TERMINAL:
    raise ConnectorError(...)   # ← lens has no retry logic; this is Orbit's job
```

## 9. Marker block duplication

Grace prepends the constitution §4 marker to every emitted file. Do not also write a second
marker. The first thing after the marker should be `from __future__ import annotations`,
then imports.

## 10. No surgical hand-edits of marker-stamped files

Files starting with the constitution §4 marker are Grace-managed. Editing them by hand
breaks the regeneration workflow — `generate --domain X` will overwrite the change. If a
generated file needs a fix, fix it in the rulebook / prompt / per-PSP spec so that the
next generation produces the correct output.

## 11. Bare `dict` / `list` fail `mypy --strict`

`mypy --strict` enforces the `type-arg` rule: every builtin generic must be parameterized.

| ✗ Fails mypy | ✓ Correct |
|---|---|
| `: dict` | `: dict[str, Any]` |
| `-> dict` | `-> dict[str, str]` |
| `: list` | `: list[PaymentAttempt]` |
| `-> list` | `-> list[str]` |

When the value type is unknown or mixed, use `dict[str, Any]` (import `Any` from `typing`).
This applies to all function signatures, class fields, and local variable annotations.

## 12. Invented `PaymentMethod` members

The locked `PaymentMethod` enum has exactly five members:
`CARD`, `UPI`, `WALLET`, `BANK_TRANSFER`, `BANK_REDIRECT`.

`NET_BANKING`, `EMI`, `PAY_LATER` do **NOT** exist. Any access to a non-existent member
causes `mypy --strict` to fail:
`error: "type[PaymentMethod]" has no attribute "NET_BANKING"`.

Map PSP groups to the closest locked member (see §12 table in `status_mapping.md`) or omit
the group from `supported_methods`. Never fabricate a member.

## 13a. `payment_link` must be `HttpUrl`, not a bare `str`

`CreateOrderResponse.payment_link` is typed `HttpUrl` (pydantic). Passing a bare Python `str`
causes mypy `--strict` to fail:

```
error: Argument "payment_link" to "CreateOrderResponse" has incompatible type "str"; expected "HttpUrl"
```

```python
# WRONG — bare str → mypy error + pydantic coercion depends on model Config:
payment_link = f"https://sandbox.cashfree.com/pg/orders/sessions/{session_id}"
return CreateOrderResponse(
    psp_order_id=…,
    payment_link=payment_link,   # ← str, not HttpUrl → mypy strict error
    …
)
```

```python
# CORRECT — coerce with HttpUrl(url) before passing:
from pydantic import HttpUrl

payment_link_url = HttpUrl(
    f"https://sandbox.cashfree.com/pg/orders/sessions/{session_id}"
)
return CreateOrderResponse(
    psp_order_id=…,
    payment_link=payment_link_url,   # ← HttpUrl ✓
    …
)
```

The self-check grep for `payment_link=<bare-str-var>` (a plain identifier without `HttpUrl(`)
is:
```
Grep(pattern="payment_link=[a-z_]+[^)]", path=<cwd>/orders, glob="connector.py")
    → ZERO matches  (every payment_link= assignment must be wrapped in HttpUrl(...))
```

## 13. `raw` vs `raw_payload` / `occurred_at` cross-use

`PaymentWebhookEvent` and `MandateWebhookEvent` have **different** field names for the raw
payload and **different** presence of `occurred_at`:

| | `PaymentWebhookEvent` | `MandateWebhookEvent` |
|---|---|---|
| raw dict | `raw_payload: dict[str, Any]` | `raw: dict[str, Any]` |
| `occurred_at` | **absent** | **present** (`datetime`) |

```python
# WRONG — swapped raw field:
PaymentWebhookEvent(…, raw=payload)           # ← ValidationError: extra field
MandateWebhookEvent(…, raw_payload=payload)   # ← ValidationError: extra field

# WRONG — occurred_at on payment event:
PaymentWebhookEvent(…, occurred_at=dt)        # ← ValidationError: extra field

# CORRECT:
PaymentWebhookEvent(…, raw_payload=payload)
MandateWebhookEvent(…, occurred_at=dt, raw=payload)
```

Both models have `extra="forbid"`, so wrong field names raise `ValidationError` at runtime and
fail pydantic model construction.

## Final self-check

Before committing, run:

```
grep -rn 'class.*Connector.*Connector' connector.py   # bare Connector base → 0 matches
grep 'register_webhook' __init__.py                    # present → ≥ 1 match
grep 'requires_lens' __init__.py                       # removed in v0.6 → 0 matches
grep 'WEBHOOK_SIGNATURE_FAILED' webhooks.py            # present → ≥ 1 match
grep -E 'Dict\[|List\[|Optional\[|Set\[' **/*.py      # deprecated aliases → 0 matches
grep 'MandatesConnector' **/*.py                       # typo → 0 matches
grep 'handle_webhook' **/*.py                          # retired → 0 matches
grep -c 'async def' subscriptions/connector.py         # lifecycle methods → ≥ 5
```
