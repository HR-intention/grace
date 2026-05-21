# Multi-Lang Connector Generation — Plan D: Python Pattern Pack (Wave 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Author the Python language pack at `grace/rulesbook/codegen-python/` so an AI coding agent can run `integrate <Connector> using grace/rulesbook/codegen-python/.gracerules` and produce a working Python connector for the `lens` shell (Plan C).

**Architecture:** Mirror the Rust pack's structure (`guides/patterns/`, `guides/types/`, `guides/quality/`, `.gracerules*` triad) but with Python code templates referencing `lens.domain_types.*` symbols and `BaseConnector` + `@connector_flow` from Plan C. Wave 1 ships 7 flow patterns + 3 payment-method patterns + Python type-system reference + Python-specific quality checks + a streamlined `.gracerules` entrypoint. Wave 2 (deferred) adds the `_add_flow` / `_add_payment_method` triad files and remaining patterns.

**Tech Stack:** Markdown only (this plan modifies the grace repo only; no Python code changes here — Plan E exercises the generated code end-to-end).

**Source spec:** [docs/superpowers/specs/2026-05-18-multi-lang-connector-generation-design.md](../specs/2026-05-18-multi-lang-connector-generation-design.md) — Section 6 (Python language pack contents).

**Depends on:** Plans A, B, C (all landed).

---

## File structure (target)

```
grace/rulesbook/codegen-python/
├── .gracerules                                       # Wave 1: new connector from scratch
├── .gracerules_add_flow                              # Wave 2 stub (points at .gracerules)
├── .gracerules_add_payment_method                    # Wave 2 stub (points at .gracerules)
├── README.md                                         # Pack overview
└── guides/
    ├── types/
    │   └── types.md                                  # Python type-system reference (Plan C symbols)
    ├── patterns/
    │   ├── pattern_authorize.md
    │   ├── pattern_psync.md
    │   ├── pattern_capture.md
    │   ├── pattern_refund.md
    │   ├── pattern_rsync.md
    │   ├── pattern_void.md
    │   ├── pattern_IncomingWebhook_flow.md
    │   └── authorize/
    │       ├── card/pattern_authorize_card.md
    │       ├── wallet/pattern_authorize_wallet.md
    │       └── upi/pattern_authorize_upi.md
    └── quality/
        └── python_quality_checks.md                  # Python-specific quality criteria
```

All Wave 1 patterns reference `../../../shared/{flows,payment_methods,quality_rubric,feedback,learnings}.md` for language-neutral concepts.

---

## Tasks

### Task 1: Directory scaffolding + README + `.gracerules` (entrypoint)

**Files:**
- Create: `rulesbook/codegen-python/README.md`
- Create: `rulesbook/codegen-python/.gracerules`
- Create: `rulesbook/codegen-python/.gracerules_add_flow` (Wave 2 stub)
- Create: `rulesbook/codegen-python/.gracerules_add_payment_method` (Wave 2 stub)

- [ ] **Step 1: Create directories**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
mkdir -p rulesbook/codegen-python/guides/{types,patterns/authorize/{card,wallet,upi},quality}
```

- [ ] **Step 2: Write `rulesbook/codegen-python/README.md`**

```markdown
# codegen-python — Python language pack

Sibling of `codegen-rust/`. Produces Python connectors for the
`lens` shell at the sibling repo.

## Entrypoints

| File | Command form | Status |
|---|---|---|
| `.gracerules` | `integrate <Connector> using grace/rulesbook/codegen-python/.gracerules` | **Wave 1 — works** |
| `.gracerules_add_flow` | `add <Flow> flow to <Connector> using grace/rulesbook/codegen-python/.gracerules_add_flow` | Wave 2 stub |
| `.gracerules_add_payment_method` | `add <Category>:<PM> to <Connector> using grace/rulesbook/codegen-python/.gracerules_add_payment_method` | Wave 2 stub |

## Wave 1 scope

- **7 flows:** Authorize, PSync, Capture, Refund, RSync, Void, IncomingWebhook
- **3 PMs:** Card, Wallet, UPI (Collect + Intent)
- Indian payment ecosystem first — UPI is mandatory, webhook dedup is required

## How it connects to the rest

- Type-system surface comes from `lens/lens/domain_types/` (Plan C). See [`guides/types/types.md`](guides/types/types.md) for the cross-reference.
- Flow definitions, prerequisite DAG, payment-method taxonomy, and quality rubric come from [`../shared/`](../shared/) — same as `codegen-rust`.
- Per-language quality checks live in [`guides/quality/python_quality_checks.md`](guides/quality/python_quality_checks.md).

## See also

- [`../codegen-rust/`](../codegen-rust/) — Rust language pack
- [`../shared/`](../shared/) — language-neutral content (flows, payment_methods, quality_rubric, feedback, learnings)
```

- [ ] **Step 3: Write `rulesbook/codegen-python/.gracerules`**

This is the main entrypoint. Keep it tight — point at supporting docs rather than inlining everything.

```markdown
# GRACE Python Codegen — New Connector Integration

You are integrating a new payment connector into `lens` (sibling of `grace/`). Your output is Python source code in `lens/connectors/<connector>/` plus a wiring update in `lens/connectors/__init__.py`.

## Inputs

| Variable | Description |
|---|---|
| `{Connector}` | Connector name in canonical casing (e.g., `Razorpay`) |
| `{connector}` | Same, lowercase (e.g., `razorpay`) — used in filenames and registry keys |
| `{base_url}` | PSP base URL (e.g., `https://api.razorpay.com/v1`) |
| `{tech_spec_path}` | Absolute or repo-relative path to the tech spec (typically `grace/rulesbook/references/{connector}/technical_specification.md`) |

## Hard rules

1. **Target shell:** `lens/lens/`. Work from that repo's root.
2. **No HTTP without async.** Every flow method is `async def` and uses `self.client` (an `httpx.AsyncClient`).
3. **No floats on money.** Use `Amount(minor_units=int, currency=Currency.X)`.
4. **No print().** Use the structlog logger; the `@connector_flow` decorator already emits standard fields.
5. **No raw secrets in logs.** PCI/PII fields (`card_number`, `cvv`, `vpa`) are auto-masked if the field name matches the masking processor; pass them through as field names, not concatenated strings.
6. **Pydantic strict.** Every connector-specific model uses `model_config = ConfigDict(extra="forbid")` so unknown PSP response fields fail fast.
7. **No mocked tests against the connector.** Integration tests hit a running uvicorn process via `httpx.AsyncClient`; mypy and `pytest --collect-only` are the build gate.

## Phases

### Phase 0: Read the tech spec
Read `{tech_spec_path}` end-to-end. Note the base URL, authentication scheme, supported flows, endpoint paths, request/response shapes, error codes, status mappings, idempotency convention, and webhook signature scheme.

### Phase 1: Scaffold the connector package

Create:
- `lens/connectors/{connector}/__init__.py` — calls `register_connector("{connector}", {Connector})`
- `lens/connectors/{connector}/connector.py` — `{Connector}(BaseConnector)` class with all 7 flow methods stubbed
- `lens/connectors/{connector}/transformers.py` — PSP-specific request/response Pydantic models + `to_*_request` / `from_*_response` transformer functions
- `lens/connectors/{connector}/auth.py` — `{Connector}Auth(BaseAuth)` with any extra credential fields the PSP needs

Append `from . import {connector}` to `lens/connectors/__init__.py` (the explicit-discovery convention from Plan C).

Wire the credential entry into `creds.json` under the connector name (use sandbox/test keys).

### Phase 2: Implement each flow

For each of the 7 flows (Authorize, PSync, Capture, Refund, RSync, Void, IncomingWebhook):
1. Read the corresponding pattern file in `guides/patterns/pattern_<flow>.md`.
2. Read the relevant payment-method pattern(s) under `guides/patterns/authorize/<category>/` (Authorize only).
3. Apply the pattern, substituting placeholders for this connector's specifics from the tech spec.
4. Run `uv run mypy lens/connectors/{connector}/` — must be clean.
5. Run `uv run pytest tests/integration/test_{connector}.py --collect-only` if you've authored that test file; if not yet authored, defer to Phase 4.

### Phase 3: Status mapping

Implement the connector's `_map_status` helpers (typically one per flow result type). Every PSP status documented in the tech spec must map to a `AttemptStatus` or `RefundStatus`. Unmapped statuses are a critical quality issue.

### Phase 4: Integration tests

Author `lens/tests/integration/test_{connector}.py` with:
- A fixture spinning up the FastAPI app + an `httpx.AsyncClient`.
- `test_authorize` — POSTs to `/v1/payments/authorize` with a sample request from the tech spec, asserts status code and decoded response shape.
- `test_psync`, `test_capture`, `test_refund`, `test_rsync`, `test_void` — analogous.
- `test_incoming_webhook` — POSTs to `/v1/webhooks/{connector}` with a sample payload (incl. signature header) and asserts `WebhookAck`.

Tests require valid `creds.json` for sandbox calls. Mark as `@pytest.mark.integration` so they can be skipped in CI without credentials.

### Phase 5: Quality review

Walk through the checks in `guides/quality/python_quality_checks.md` and the cross-cutting checks in `../shared/quality_rubric.md`. The score must be ≥ 60.

Log lessons to `../shared/feedback.md` with the `[lang:python]` tag.

## Supporting references

- Type system: [`guides/types/types.md`](guides/types/types.md)
- Pattern files: [`guides/patterns/`](guides/patterns/)
- Quality checks: [`guides/quality/python_quality_checks.md`](guides/quality/python_quality_checks.md)
- Shared content: [`../shared/`](../shared/)
```

- [ ] **Step 4: Write `rulesbook/codegen-python/.gracerules_add_flow` (Wave 2 stub)**

```markdown
# GRACE Python Codegen — Add Flow (Wave 2 stub)

Wave 2 work — not yet implemented in detail. For Wave 1, use the main
`.gracerules` entrypoint and implement all 7 flows from scratch. When this
file is fully authored, it will support incremental flow addition to an
existing Python connector (mirroring `../codegen-rust/.gracerules_add_flow`).

Until then, if you need to add a single flow:
1. Open `.gracerules` and consult Phase 2 for the relevant flow.
2. Apply the matching pattern from `guides/patterns/`.
3. Skip the scaffolding steps (Phase 1) — they're already done for an existing connector.
```

- [ ] **Step 5: Write `rulesbook/codegen-python/.gracerules_add_payment_method` (Wave 2 stub)**

```markdown
# GRACE Python Codegen — Add Payment Method (Wave 2 stub)

Wave 2 work — not yet implemented in detail. For Wave 1, use the main
`.gracerules` entrypoint. When fully authored, this file will mirror
`../codegen-rust/.gracerules_add_payment_method` syntax for adding
specific payment methods (e.g., `add UPI:Collect,Intent to Razorpay`).

Until then, to add a payment method:
1. Read the relevant pattern in `guides/patterns/authorize/<category>/`.
2. Extend the connector's existing `authorize` method body to handle the new payment-method variant.
3. Add transformer code and types in `transformers.py`.
```

- [ ] **Step 6: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/codegen-python/
git commit -m "feat(codegen-python): scaffold pack with README + .gracerules triad

Wave 1 entrypoint (.gracerules) covers new-connector-from-scratch flow
end-to-end. _add_flow and _add_payment_method are Wave 2 stubs that
point at .gracerules for now. Pattern files come in subsequent commits."
```

---

### Task 2: `guides/types/types.md` — Python type-system reference

**Files:**
- Create: `rulesbook/codegen-python/guides/types/types.md`

This file is the contract between the rulesbook and `lens/lens/domain_types/`. Every name listed here is asserted importable by Plan C's contract test.

- [ ] **Step 1: Write `guides/types/types.md`**

```markdown
# Python type-system reference

Authoritative cross-reference between symbols the rulesbook patterns name
and what exists in `lens/lens/domain_types/`.

Every name in this file MUST be importable from `lens.domain_types`.
The contract test at `lens/tests/contract/test_types_contract.py`
fails the build if any name drifts.

## Top-level imports

All names below are re-exported from `lens.domain_types`:

```python
from lens.domain_types import (
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

`IncomingWebhook` does not use this pattern — see [`pattern_IncomingWebhook_flow.md`](../patterns/pattern_IncomingWebhook_flow.md).

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

These come from `lens.connectors._base` and `lens.connectors._registry`:

```python
from lens.connectors._base import BaseConnector, connector_flow
from lens.connectors._registry import register_connector

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

This file is enforced by `tests/contract/test_types_contract.py` in `lens`. If a name listed here is missing from `lens.domain_types`, the contract test fails and Plan D's codegen is blocked.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/codegen-python/guides/types/types.md
git commit -m "docs(codegen-python): add Python type-system reference

Cross-references every domain_types symbol Plan C's contract test pins.
Patterns reference this file rather than restating type shapes."
```

---

### Task 3: Core flow patterns (6 files)

**Files:**
- Create: `rulesbook/codegen-python/guides/patterns/pattern_authorize.md`
- Create: `rulesbook/codegen-python/guides/patterns/pattern_psync.md`
- Create: `rulesbook/codegen-python/guides/patterns/pattern_capture.md`
- Create: `rulesbook/codegen-python/guides/patterns/pattern_refund.md`
- Create: `rulesbook/codegen-python/guides/patterns/pattern_rsync.md`
- Create: `rulesbook/codegen-python/guides/patterns/pattern_void.md`

Each pattern follows the 6-section structure: Quick Start, Prerequisites, Template, Legacy (skip if N/A), Testing Strategy, Validation Checklist.

For brevity, the FULL content of `pattern_authorize.md` is below; the others follow the same skeleton with the appropriate flow's request/response types, HTTP method, and status mapping logic.

- [ ] **Step 1: Write `pattern_authorize.md`**

```markdown
# Pattern: Authorize flow (Python)

## 🎯 Quick Start

Implements `{Connector}.authorize(data: PaymentData[AuthorizeRequest, AuthorizeResponse])`.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{base_url}` — already on the class; you reference `self.base_url` indirectly via `self.client`
- `{authorize_endpoint}` — PSP authorize path (e.g., `/v1/orders` or `/payments/create`)
- `{Connector}AuthorizeRequest` / `{Connector}AuthorizeResponse` — PSP-specific Pydantic models you define in `transformers.py`

## 📋 Prerequisites

None — Authorize is the entry point for any new connector. All other flows depend on it.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `lens/connectors/{connector}/connector.py`:

```python
from lens.connectors._base import BaseConnector, connector_flow
from lens.connectors._registry import register_connector
from lens.domain_types import (
    AttemptStatus, AuthorizeRequest, AuthorizeResponse, Flow, PaymentData,
)

from .auth import {Connector}Auth
from .transformers import (
    {Connector}AuthorizeRequest, {Connector}AuthorizeResponse,
    to_authorize_request, from_authorize_response,
)


class {Connector}(BaseConnector):
    name = "{connector}"
    base_url = "{base_url}"
    AuthCls = {Connector}Auth

    @connector_flow(flow=Flow.AUTHORIZE)
    async def authorize(
        self, data: PaymentData[AuthorizeRequest, AuthorizeResponse]
    ) -> PaymentData[AuthorizeRequest, AuthorizeResponse]:
        psp_request: {Connector}AuthorizeRequest = to_authorize_request(data.request)
        http_response = await self.client.post(
            "{authorize_endpoint}",
            json=psp_request.model_dump(by_alias=True, exclude_none=True),
            headers={
                **self._auth_headers(),
                "Idempotency-Key": data.idempotency_key or "",
            },
        )
        http_response.raise_for_status()
        psp_response = {Connector}AuthorizeResponse.model_validate_json(http_response.text)
        data.response = from_authorize_response(psp_response)
        data.status = _map_status(psp_response.status)
        return data

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth.api_key}"}


def _map_status(psp_status: str) -> AttemptStatus:
    # Fill in per the tech spec's "Status Mapping" section.
    # Every documented PSP status must have an entry — unmapped = critical quality issue.
    return {
        "created": AttemptStatus.PENDING,
        "authorized": AttemptStatus.AUTHORIZED,
        "captured": AttemptStatus.CHARGED,
        "failed": AttemptStatus.FAILURE,
        # ... add every status the tech spec lists
    }[psp_status]


register_connector("{connector}", {Connector})
```

In `lens/connectors/{connector}/transformers.py`:

```python
from pydantic import BaseModel, ConfigDict, Field
from lens.domain_types import (
    AttemptStatus, AuthorizeRequest, AuthorizeResponse,
    CardData, UpiData, WalletData,
)


class {Connector}AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Fill in PSP-specific fields per the tech spec
    amount: int                          # PSP-side: minor units
    currency: str
    payment_method_type: str
    card: Optional[dict] = None          # nested per the tech spec
    upi: Optional[dict] = None
    # ... etc


class {Connector}AuthorizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str
    # ... whatever the PSP returns


def to_authorize_request(req: AuthorizeRequest) -> {Connector}AuthorizeRequest:
    # Map the domain request to PSP-specific shape
    pm_block = _payment_method_block(req.payment_method)
    return {Connector}AuthorizeRequest(
        amount=req.amount.minor_units,
        currency=req.amount.currency.value,
        payment_method_type=_pm_type(req.payment_method),
        **pm_block,
    )


def from_authorize_response(resp: {Connector}AuthorizeResponse) -> AuthorizeResponse:
    return AuthorizeResponse(
        connector_payment_id=resp.id,
        status=AttemptStatus.PENDING,  # decorator overrides with mapped value
        raw_response=resp.model_dump(),
    )


def _payment_method_block(pm) -> dict:
    if isinstance(pm, CardData):
        return {"card": {"number": pm.card_number, "exp_month": pm.card_exp_month, ...}}
    if isinstance(pm, UpiData):
        return {"upi": {"vpa": pm.vpa}} if pm.upi_flow.value == "collect" else {"upi": {}}
    if isinstance(pm, WalletData):
        return {"wallet": {"type": pm.wallet_type.value, "token": pm.token}}
    raise NotImplementedError(f"Payment method {type(pm).__name__} not supported")


def _pm_type(pm) -> str:
    if isinstance(pm, CardData): return "card"
    if isinstance(pm, UpiData): return "upi"
    if isinstance(pm, WalletData): return "wallet"
    raise NotImplementedError(...)
```

Refer to the per-PM patterns under `authorize/{card,wallet,upi}/` for payment-method-specific transformer logic.

## 🧪 Testing Strategy

Author `lens/tests/integration/test_{connector}.py`:

```python
import pytest
from fastapi.testclient import TestClient

from lens.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_authorize_card(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-123",
            "request": {
                "amount": {"minor_units": 10000, "currency": "INR"},
                "payment_method": {
                    "card_number": "<test card from tech spec>",
                    "card_exp_month": "12",
                    "card_exp_year": "2030",
                    "card_holder_name": "Test Customer",
                    "card_cvc": "123",
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("pending", "authorized", "charged")
    assert body["response"]["connector_payment_id"]
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `to_authorize_request` handles all 3 payment methods (Card, Wallet, UPI) — even if the connector only supports a subset (raise `NotImplementedError` for unsupported).
- [ ] `from_authorize_response` returns a fully-populated `AuthorizeResponse` (no `None` for fields the PSP returned).
- [ ] `_map_status` has an entry for EVERY status the tech spec documents. Unmapped statuses are a critical issue.
- [ ] Idempotency-Key header is sent (decorator provides the value via `data.idempotency_key`).
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
```

- [ ] **Step 2: Write the other 5 core-flow patterns**

Each follows the same skeleton as `pattern_authorize.md`. Differences:

- **`pattern_psync.md`**: HTTP GET to `{psync_endpoint}` keyed by `connector_payment_id`. No request body. Response maps to `AttemptStatus`. Prerequisites: Authorize.
- **`pattern_capture.md`**: HTTP POST to `{capture_endpoint}` with `amount_to_capture` (minor units). Prerequisites: Authorize. Status mapping like Authorize.
- **`pattern_refund.md`**: HTTP POST to `{refund_endpoint}` with `refund_amount`. Returns `connector_refund_id` (distinct from `connector_payment_id`). Status maps to `RefundStatus`. Prerequisites: Capture (or Authorize for auth-and-capture-in-one PSPs).
- **`pattern_rsync.md`**: HTTP GET to `{rsync_endpoint}` keyed by `connector_refund_id`. Status to `RefundStatus`. Prerequisites: Refund.
- **`pattern_void.md`**: HTTP POST/DELETE to `{void_endpoint}`. Some PSPs require a reason field. Prerequisites: Authorize.

For each, write the 6-section file mirroring `pattern_authorize.md`'s shape with the flow-specific HTTP method, endpoint placeholder, request/response Pydantic field list, transformer functions, status enum, and prerequisite. Each file should be ~150-200 lines.

To keep the plan tractable, use the following abbreviated template for the remaining 5 — fill in flow-specifics per the spec section on each flow.

```markdown
# Pattern: {FlowName} flow (Python)

## 🎯 Quick Start
Implements `{Connector}.{flow_method}(data: PaymentData[{Flow}Request, {Flow}Response])`.

Placeholders: `{Connector}`, `{connector}`, `{{flow}_endpoint}` (per tech spec).

## 📋 Prerequisites
{Prerequisites from shared/flows.md — for {FlowName}, this is {prereq_list}}

## 🏗️ Template
{Full async def body with @connector_flow decorator, http call, transformers, status mapping. Mirror pattern_authorize.md but with the flow's HTTP method, endpoint placeholder, and types.}

## 🧪 Testing Strategy
{pytest integration test posting to /v1/payments/{flow}}

## ✅ Validation Checklist
{Same shape as pattern_authorize.md, scoped to this flow's concerns}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/codegen-python/guides/patterns/pattern_*.md
git commit -m "feat(codegen-python): add 6 core-flow patterns

Authorize, PSync, Capture, Refund, RSync, Void — each with template,
testing strategy, and validation checklist. References shared/flows.md
for prerequisite DAG."
```

---

### Task 4: IncomingWebhook + UPI patterns (3 files, tightly linked)

**Files:**
- Create: `rulesbook/codegen-python/guides/patterns/pattern_IncomingWebhook_flow.md`
- Create: `rulesbook/codegen-python/guides/patterns/authorize/upi/pattern_authorize_upi.md`
- Create: `rulesbook/codegen-python/guides/patterns/authorize/card/pattern_authorize_card.md`

Bundling these because UPI status arrives via webhook on most Indian PSPs — patterns reference each other tightly.

- [ ] **Step 1: Write `pattern_IncomingWebhook_flow.md`**

```markdown
# Pattern: IncomingWebhook flow (Python)

## 🎯 Quick Start

Implements `{Connector}.incoming_webhook(raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent`.

Webhooks are how UPI payment status reaches us — PSync polling is too slow for production UPI. Every Indian PSP webhook is at-least-once, so deduplication is required.

Placeholders: `{Connector}`, `{connector}`, `{signature_header_name}` (e.g., `x-razorpay-signature`), `{event_id_field}` (e.g., `event.id` or `data.id` per the tech spec).

## 📋 Prerequisites

PSync (per `../../../shared/flows.md`). Conceptually the webhook delivers the same status PSync would fetch, just push-style.

## 🏗️ Template

In `lens/connectors/{connector}/connector.py`, add the webhook handler:

```python
import hmac
import hashlib
import json

from lens.domain_types import ConnectorError, WebhookEvent


class {Connector}(BaseConnector):
    # ... other methods ...

    async def incoming_webhook(
        self, raw_payload: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        # Step 1: Signature verification
        received_sig = headers.get("{signature_header_name}", "")
        expected_sig = hmac.new(
            self.auth.webhook_secret.encode(),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(received_sig, expected_sig):
            raise ConnectorError("webhook signature mismatch", retryable=False)

        # Step 2: Parse + extract event_id
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            raise ConnectorError(f"webhook payload not JSON: {e}", retryable=False)

        event_id = payload.get("{event_id_field}")
        if not event_id:
            raise ConnectorError("webhook missing event_id", retryable=False)

        # Step 3: Dedup
        # Note: dedup_store is available via FastAPI app.state but the connector body
        # doesn't have direct access to it. The router passes the dedup_store reference
        # via a contextvar set by the lifespan. Plan E's Razorpay implementation
        # wires this through.
        # For now, the connector returns WebhookEvent.duplicate(...) ONLY if it has
        # internal knowledge of duplicates (rare). The dedup check is handled by
        # the router layer.

        # Step 4: Normalize to WebhookEvent
        event_type = payload.get("event", "unknown")
        return WebhookEvent(
            connector_name="{connector}",
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
```

The router (`api/routers/webhooks.py`) is responsible for invoking the dedup store before returning the result. Generated connectors should focus on signature + parse + normalize.

## 🧪 Testing Strategy

```python
import hmac
import hashlib
import json
import pytest


@pytest.mark.integration
def test_incoming_webhook_valid_signature(client):
    payload = {"event": "payment.captured", "{event_id_field}": "evt_test_123", ...}
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"<webhook_secret_from_creds>", raw, hashlib.sha256).hexdigest()

    response = client.post(
        "/v1/webhooks/{connector}",
        headers={
            "Authorization": "Bearer test",
            "{signature_header_name}": sig,
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == "evt_test_123"
    assert body["duplicate"] is False


@pytest.mark.integration
def test_incoming_webhook_invalid_signature_rejected(client):
    payload = {"event": "payment.captured", "id": "evt_test_456"}
    raw = json.dumps(payload).encode()

    response = client.post(
        "/v1/webhooks/{connector}",
        headers={
            "Authorization": "Bearer test",
            "{signature_header_name}": "wrong_signature",
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert response.status_code == 400
```

## ✅ Validation Checklist

- [ ] Signature verification uses `hmac.compare_digest` (constant-time) — NOT `==`.
- [ ] Missing or empty signature header → `ConnectorError`, NOT silent acceptance.
- [ ] JSON parse failure → `ConnectorError` with retryable=False (replaying won't help).
- [ ] Missing event_id → `ConnectorError`. Without an event_id we can't dedup, which means duplicate events cause double-processing.
- [ ] `mypy --strict` clean.
```

- [ ] **Step 2: Write `authorize/upi/pattern_authorize_upi.md`**

```markdown
# Pattern: UPI payment method (Authorize, Python)

UPI is the primary payment rail in India. Every Indian connector MUST support it.

## 🎯 Quick Start

Extends `to_authorize_request` (in `transformers.py`) to handle `UpiData` payment methods.

Two sub-flows:
- **UPI Collect** — customer's VPA is provided; PSP pushes a payment request to their UPI app; status arrives via webhook
- **UPI Intent** — PSP returns a deep link (`upi://pay?...`); customer's UPI app opens; status arrives via webhook

Placeholders: `{Connector}`, `{connector}`, `{upi_endpoint_field}` (PSP-specific JSON field name for VPA).

## 📋 Prerequisites

Authorize flow (per `../../../../shared/flows.md`). UPI is a payment-method variant of Authorize.

## 🏗️ Template

Extend the connector's `_payment_method_block` and `_pm_type` helpers:

```python
from lens.domain_types import RedirectionData, UpiData, UpiFlowType


def _payment_method_block(pm) -> dict:
    if isinstance(pm, UpiData):
        if pm.upi_flow == UpiFlowType.COLLECT:
            if not pm.vpa:
                raise ValueError("VPA required for UPI Collect")
            return {"upi": {"{upi_endpoint_field}": pm.vpa, "flow": "collect"}}
        elif pm.upi_flow == UpiFlowType.INTENT:
            return {"upi": {"flow": "intent"}}
        else:
            raise NotImplementedError(f"UPI flow {pm.upi_flow} not supported")
    # ... fall through to other PMs ...
```

And in `from_authorize_response`, populate `redirection_data` for UPI Intent:

```python
def from_authorize_response(resp: {Connector}AuthorizeResponse) -> AuthorizeResponse:
    redirection = None
    if resp.upi_intent_url:  # PSP-specific field name from tech spec
        redirection = RedirectionData(
            method="INTENT",
            url=resp.upi_intent_url,  # deep link like upi://pay?pa=...
        )
    return AuthorizeResponse(
        connector_payment_id=resp.id,
        status=_map_status(resp.status),
        redirection_data=redirection,
        raw_response=resp.model_dump(),
    )
```

For UPI Collect, no `redirection_data` is set; the customer's UPI app receives a push notification from the PSP. The connector returns `AttemptStatus.PENDING`; the eventual `CHARGED` or `FAILURE` status arrives via `incoming_webhook` (see [`../../../pattern_IncomingWebhook_flow.md`](../../../pattern_IncomingWebhook_flow.md)).

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_upi_collect(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-upi-collect",
            "request": {
                "amount": {"minor_units": 100, "currency": "INR"},
                "payment_method": {
                    "upi_flow": "collect",
                    "vpa": "test@upi",  # sandbox VPA from PSP docs
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"  # collect waits for customer approval


@pytest.mark.integration
def test_authorize_upi_intent(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-upi-intent",
            "request": {
                "amount": {"minor_units": 100, "currency": "INR"},
                "payment_method": {"upi_flow": "intent"},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["redirection_data"]["method"] == "INTENT"
    assert body["response"]["redirection_data"]["url"].startswith("upi://")
```

## ✅ Validation Checklist

- [ ] Both `UpiFlowType.COLLECT` and `UpiFlowType.INTENT` are handled.
- [ ] Collect without `vpa` raises a clear error.
- [ ] Intent returns `RedirectionData(method="INTENT", url=upi://...)`.
- [ ] Status for both starts at `PENDING` — final status arrives via webhook.
- [ ] VPA values are not logged in plaintext (mask via `mask_vpa` or use field-name `vpa` in structlog kwargs so the masking processor catches it).
```

- [ ] **Step 3: Write `authorize/card/pattern_authorize_card.md`**

```markdown
# Pattern: Card payment method (Authorize, Python)

## 🎯 Quick Start

Extends `to_authorize_request` to handle `CardData` payment methods.

Placeholders: `{Connector}`, `{connector}`, `{card_field_names}` (per tech spec — common variants: `card.number`, `card_number`, `card.pan`).

## 📋 Prerequisites

Authorize flow.

## 🏗️ Template

```python
from lens.domain_types import CardData


def _payment_method_block(pm) -> dict:
    if isinstance(pm, CardData):
        return {
            "card": {
                "number": pm.card_number,
                "exp_month": pm.card_exp_month,
                "exp_year": pm.card_exp_year,
                "name": pm.card_holder_name,
                "cvv": pm.card_cvc,
                # Some PSPs require additional fields per the tech spec:
                # "issuer": pm.card_issuer,
            }
        }
    # ... fall through to other PMs ...
```

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_card(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-card",
            "request": {
                "amount": {"minor_units": 10000, "currency": "INR"},
                "payment_method": {
                    "card_number": "<sandbox card from tech spec>",
                    "card_exp_month": "12",
                    "card_exp_year": "2030",
                    "card_holder_name": "Test Customer",
                    "card_cvc": "123",
                },
            },
        },
    )
    assert response.status_code == 200
```

## ✅ Validation Checklist

- [ ] All five required fields (number, exp_month, exp_year, holder_name, cvc) are passed through.
- [ ] Card number is never logged unmasked. The structlog masker handles fields named `card_number`, `pan`, `card_pan`; ensure the connector logs using these key names.
- [ ] CVV is never logged at all (masker redacts to `***` unconditionally).
- [ ] 3DS / SCA flow: if the PSP returns a redirect URL for 3DS, surface it via `RedirectionData(method="POST", url=..., form_fields=...)`.
```

- [ ] **Step 4: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/codegen-python/guides/patterns/
git commit -m "feat(codegen-python): add IncomingWebhook + UPI + Card patterns

UPI patterns cover both Collect and Intent sub-flows. Webhook pattern
covers signature verification + dedup contract. Card pattern covers
the canonical 5-field shape plus 3DS hand-off via RedirectionData."
```

---

### Task 5: Wallet pattern + quality checks

**Files:**
- Create: `rulesbook/codegen-python/guides/patterns/authorize/wallet/pattern_authorize_wallet.md`
- Create: `rulesbook/codegen-python/guides/quality/python_quality_checks.md`

- [ ] **Step 1: Write `authorize/wallet/pattern_authorize_wallet.md`**

```markdown
# Pattern: Wallet payment method (Authorize, Python)

## 🎯 Quick Start

Extends `to_authorize_request` to handle `WalletData` payment methods.

Wallets include Apple Pay, Google Pay, PayPal, Samsung Pay, Paytm, PhonePe. The PSP-specific request shape varies — most accept an opaque token from the wallet provider.

Placeholders: `{Connector}`, `{connector}`, `{wallet_token_field}` (per tech spec).

## 📋 Prerequisites

Authorize flow.

## 🏗️ Template

```python
from lens.domain_types import WalletData, WalletType


def _payment_method_block(pm) -> dict:
    if isinstance(pm, WalletData):
        return {
            "wallet": {
                "type": pm.wallet_type.value,  # "apple_pay", "google_pay", etc.
                "{wallet_token_field}": pm.token,
                **({"email": pm.email} if pm.email else {}),
                **({"phone": pm.phone} if pm.phone else {}),
            }
        }
    # ... fall through ...
```

Some wallets (Apple Pay, Google Pay) require additional cryptogram/network-token fields. Extend `WalletData` via a per-connector model in `transformers.py` if the PSP needs them — do NOT extend the shared `WalletData` in `lens/lens/domain_types/pm_models.py`.

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_wallet_paytm(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-wallet",
            "request": {
                "amount": {"minor_units": 1000, "currency": "INR"},
                "payment_method": {
                    "wallet_type": "paytm",
                    "phone": "9876543210",
                },
            },
        },
    )
    assert response.status_code == 200
```

## ✅ Validation Checklist

- [ ] Wallet type maps to the PSP's expected string (per tech spec).
- [ ] Token is required for Apple/Google Pay; phone is typical for Indian wallets (Paytm, PhonePe).
- [ ] Token values are not logged plaintext (the masker doesn't catch `token` by default; use field name `wallet_token` or mask manually).
```

- [ ] **Step 2: Write `guides/quality/python_quality_checks.md`**

```markdown
# Python-specific quality checks

These layer on top of the language-neutral checks in `../../../shared/quality_rubric.md`. The Quality Guardian applies both lists when scoring a Python connector.

## Critical (deduct 20 points each)

- All public connector methods are `async def`.
- `@connector_flow(flow=Flow.<NAME>)` is applied to every flow method (Authorize, PSync, Capture, Refund, RSync, Void). Missing decorator = no logging / no error normalization.
- PSP-specific Pydantic models use `model_config = ConfigDict(extra="forbid")`.
- `register_connector("{connector}", {Connector})` is called from the connector's `__init__.py`.
- The connector module is imported from `lens/connectors/__init__.py` (explicit-discovery convention from Plan C).
- `mypy --strict lens/connectors/{connector}/` passes.
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
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/codegen-python/guides/
git commit -m "feat(codegen-python): add wallet pattern + Python quality checks

Wallet pattern handles WalletType variants. python_quality_checks.md
defines per-language checks layered on top of shared/quality_rubric.md."
```

---

### Task 6: Acceptance — run pattern auditor + verify

**Read-only verification.**

- [ ] **Step 1: Dispatch the `rulesbook-pattern-auditor` agent on each new pattern**

You may use the new specialized agent type `rulesbook-pattern-auditor`. Dispatch it once per pattern file (or as a single batch if the agent supports it).

For each of these 10 files, dispatch the auditor:
- `rulesbook/codegen-python/guides/patterns/pattern_authorize.md`
- `rulesbook/codegen-python/guides/patterns/pattern_psync.md`
- `rulesbook/codegen-python/guides/patterns/pattern_capture.md`
- `rulesbook/codegen-python/guides/patterns/pattern_refund.md`
- `rulesbook/codegen-python/guides/patterns/pattern_rsync.md`
- `rulesbook/codegen-python/guides/patterns/pattern_void.md`
- `rulesbook/codegen-python/guides/patterns/pattern_IncomingWebhook_flow.md`
- `rulesbook/codegen-python/guides/patterns/authorize/card/pattern_authorize_card.md`
- `rulesbook/codegen-python/guides/patterns/authorize/wallet/pattern_authorize_wallet.md`
- `rulesbook/codegen-python/guides/patterns/authorize/upi/pattern_authorize_upi.md`

NOTE: The auditor was authored for Rust patterns and checks Rust-specific concerns (`RouterDataV2`, `macro_connector_implementation!`, etc.). For Python patterns, some checks won't apply. Use the auditor's structural feedback (sections present, prerequisites valid, wiring) and ignore its language-specific Rust complaints.

- [ ] **Step 2: Verify the wiring grep**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
grep -l 'pattern_' rulesbook/codegen-python/.gracerules
ls -1 rulesbook/codegen-python/guides/patterns/*.md rulesbook/codegen-python/guides/patterns/authorize/*/*.md | sort
```

The first command should find the .gracerules referencing patterns (it does via the "Phase 2: Implement each flow" instruction). The second lists all 10 pattern files.

- [ ] **Step 3: Verify cross-references resolve**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
# Every ../shared/*.md reference from codegen-python should resolve
for ref in $(grep -hoE '\.\./[a-zA-Z_/-]+\.md' rulesbook/codegen-python/.gracerules rulesbook/codegen-python/guides/**/*.md rulesbook/codegen-python/guides/**/**/*.md 2>/dev/null | sort -u); do
    target="rulesbook/codegen-python/$ref"
    test -e "$target" && echo "OK: $ref" || echo "BROKEN: $ref"
done
```

All references should resolve. If any are broken, hand-fix and commit a small fix.

- [ ] **Step 4: No commit** (this task is verification-only unless fixes were needed)

---

### Task 7: Update CLAUDE.md + top-level docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md` (if mentions Python is unsupported / "rust only")

- [ ] **Step 1: Update CLAUDE.md**

Find the "Repository layout" section or the rulesbook description. Add `codegen-python/` to the tree:

```
│   ├── codegen-python/                # Python language pack (Wave 1)
│   │   ├── .gracerules                # Entrypoint for new connector
│   │   ├── .gracerules_add_flow       # Wave 2 stub
│   │   ├── .gracerules_add_payment_method  # Wave 2 stub
│   │   └── guides/
│   │       ├── types/types.md
│   │       ├── patterns/              # 10 Wave 1 patterns (7 flows + 3 PMs)
│   │       └── quality/python_quality_checks.md
```

Add or update the prose that lists supported target languages. Mention that Python is now Wave 1 ready alongside Rust.

- [ ] **Step 2: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add CLAUDE.md README.md
git commit -m "docs: announce codegen-python pack (Wave 1)

CLAUDE.md tree now shows codegen-python/ alongside codegen-rust/.
Both packs share rulesbook/shared/ for language-neutral content."
```

---

## Plan D acceptance summary

The plan is done when:
- All 5 task commits land on `python-support`
- All 10 Wave 1 pattern files exist
- The `.gracerules` entrypoint reads end-to-end coherently
- `guides/types/types.md` lists every symbol Plan C's contract test pins
- `guides/quality/python_quality_checks.md` is the per-language layer
- Cross-references resolve (Task 6 audit clean)
- CLAUDE.md mentions the new pack

After Plan D:
- An AI agent can run `integrate Razorpay using grace/rulesbook/codegen-python/.gracerules` and produce a working Python connector in `lens/`.
- Plan E (Razorpay E2E) becomes feasible.

---

## Self-review notes

Spec coverage:
- ✓ Section 6.1 entrypoints (.gracerules triad) — Task 1
- ✓ Section 6.2 Wave 1 pattern list (7 flows + 3 PMs) — Tasks 3, 4, 5
- ✓ Section 6.4 pattern file structure (6 sections) — every pattern file follows
- ✓ Section 6.5 Python type-system reference — Task 2
- ✓ Section 6.6 Python-specific quality checks — Task 5

Out of scope (Wave 2 / later plans):
- Full `.gracerules_add_flow` and `.gracerules_add_payment_method` (stubs only in Wave 1)
- BankTransfer, BankDebit, BankRedirect, BNPL, Crypto, GiftCard, MobilePayment, Reward PM patterns
- SetupMandate, RepeatPayment, MandateRevoke (UPI Autopay) — explicitly Wave 2 per design spec Section 11

Placeholders: every step has concrete content or commands.
