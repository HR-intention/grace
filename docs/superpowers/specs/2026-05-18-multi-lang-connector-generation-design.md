# Multi-Language Connector Generation — Design

**Date:** 2026-05-18
**Status:** Revised after independent review — awaiting user re-approval
**Target audience:** Grace maintainers, future `lens` bootstrap team
**Revision notes:** All 6 critical issues, 5 significant concerns, and 7 open questions from the independent review have been addressed. Phase order has been changed (shell-first); decorator/typing contracts are now concrete; lifecycle, registry, logging, masking, idempotency, webhook secrets, dedup, and `creds.json` sharing are all pinned.

---

## 1. Problem

Grace currently produces only Rust connectors for `connector-service` (Juspay UCS). Symplora needs to extend Grace to also generate Python connectors for a not-yet-built `lens` service, with TypeScript planned as a later addition.

**Primary market constraint:** Indian payment ecosystem. UPI is a mandatory first-class flow in any MVP — it is not "advanced" or "deferred." UPI webhooks are at-least-once and require deduplication; UPI Intent payments return a deep link, not a redirect URL; PCI-style logging requires VPA masking. These are Wave 1 design constraints, not Wave 2 polish.

## 2. Scope

**In scope:**
- Restructuring `rulesbook/` to support multiple languages with shared core concepts
- A new Python language pack (`rulesbook/codegen-python/`)
- `--target-lang` flag on `grace techspec` (defaults to `python`; loud warning when target repo is absent)
- Workflow agents (`workflow/*.md`) parameterized by language
- Quality Guardian extended with shared and Python-specific checks
- An opinionated default shape for `lens` (the target service)
- Wave 1 MVP: 7 flows + 3 payment methods (incl. UPI Collect/Intent + dedup)

**Out of scope (future work):**
- TypeScript language pack
- A formal "language pack" plugin schema — revisit if/when a 4th language is added
- Migration of existing Rust connectors to a different shape — Rust output remains exactly as today
- UPI Autopay / eMandate (SetupMandate + RepeatPayment + MandateRevoke) — Wave 2 only. Indian merchants asking for "UPI" often mean recurring; this is an explicit, surfaced non-MVP boundary

## 3. Approach summary

Selected: **Approach A — Sibling rulesbooks with a shared spine.**

- `rulesbook/codegen/` → renamed to `rulesbook/codegen-rust/`
- New sibling: `rulesbook/codegen-python/`
- Language-neutral concepts (flow definitions, prerequisite DAG, quality formula, tech-spec template, feedback database) extracted into `rulesbook/shared/`
- Each language pack contains its own pattern templates, type-system reference, and language-specific quality checks

`grace techspec` produces a single language-neutral tech spec (the spec describes the external PSP API, not the connector code). The `--target-lang` flag drives the *next-step hint* the CLI prints, the workflow-state value downstream consumers can read, and a safety check that the target service repo exists before printing the hint.

Workflow agents (`workflow/*.md`) take a `{LANG}` parameter selecting per-language build/test commands, rulesbook paths, working directory, and commit globs via a config block at the top of `2.3_codegen.md`.

## 4. Repository layout

### 4.1 New shape

```
rulesbook/
├── shared/                              # NEW — language-neutral content
│   ├── flows.md                         # Authoritative flow list + prerequisite DAG
│   ├── payment_methods.md               # Payment-method categories + types
│   ├── quality_rubric.md                # Scoring formula + cross-cutting checks
│   ├── feedback.md                      # Moved; entries tagged [lang:rust|python|*]
│   ├── learnings.md                     # Moved from codegen/guides/learnings/
│   └── tech_spec_template.md            # Moved from codegen/connector_integration/template/
├── codegen-rust/                        # RENAMED from rulesbook/codegen/
│   ├── .gracerules
│   ├── .gracerules_add_flow
│   ├── .gracerules_add_payment_method
│   ├── add_connector.sh
│   ├── guides/
│   │   ├── patterns/                    # Rust pattern templates (unchanged)
│   │   ├── types/types.md               # UCS Rust type system (RouterDataV2, etc.)
│   │   └── quality/                     # Rust-only quality checks
│   └── connector_integration/template/  # Existing template-generation/ subdir preserved
├── codegen-python/                      # NEW
│   ├── .gracerules
│   ├── .gracerules_add_flow
│   ├── .gracerules_add_payment_method
│   └── guides/
│       ├── patterns/                    # Python pattern templates (Wave 1)
│       │   ├── pattern_authorize.md
│       │   ├── pattern_psync.md
│       │   ├── pattern_capture.md
│       │   ├── pattern_refund.md
│       │   ├── pattern_rsync.md
│       │   ├── pattern_void.md
│       │   ├── pattern_IncomingWebhook_flow.md
│       │   └── authorize/
│       │       ├── card/pattern_authorize_card.md
│       │       ├── wallet/pattern_authorize_wallet.md
│       │       └── upi/pattern_authorize_upi.md
│       ├── types/types.md               # Python type system reference
│       └── quality/                     # Python-only quality checks
└── references/                          # Per-connector tech specs (unchanged, gitignored)
```

### 4.2 What moves into `rulesbook/shared/`

| Item | Why it is language-neutral |
|---|---|
| Flow definitions + prerequisite DAG | "Refund needs Capture" is invariant across languages |
| Payment-method categories | UPI, Card, Wallet, etc. are payment concepts, not code constructs |
| Quality scoring formula | The 100 - 20·Crit - 5·Warn - 1·Sug formula applies uniformly |
| Cross-cutting quality checks | Defined behaviorally, applied per language by Quality Guardian |
| `feedback.md` | Historical lessons; cross-cutting lessons stay shared, lang-specific tagged |
| Tech-spec template | Describes the external API, not the code |

### 4.3 What stays per-language

| Item | Why language-specific |
|---|---|
| Pattern files | Concrete code templates differ between Rust and Python |
| `guides/types/types.md` | Type-system imports and shapes are language-native |
| `guides/quality/` (lang-specific subset) | Per-language code-quality checks |
| `.gracerules*` entrypoints | Each language pack has its own triad |

## 5. CLI changes

### 5.1 `--target-lang` flag

Added to `grace techspec`:

```python
@click.option('-l', '--target-lang',
              type=click.Choice(['rust', 'python'], case_sensitive=False),
              default='python',
              help='Target language for codegen. Default: python.')
```

- Default: `python` — strategic direction; existing scripts that omit the flag will now produce Python-targeted output
- Threaded through `run_techspec_workflow` → `TechspecWorkflow.execute` → `TechspecWorkflowState["target_lang"]`
- Stored as a workflow-state field for downstream consumers (e.g., the `-e` enhancer may bias section emphasis)

### 5.2 Target-repo-exists safety check (addresses Critical #5)

The default `python` is convenient but risky during the rollout window — `lens` doesn't exist yet in Phases 0–2. Mitigation: `output_node` resolves the expected target repo path, and if absent, prints a loud warning and a recovery hint rather than silently producing an orphaned spec.

```python
# In src/workflows/techspec/nodes/output_node.py

def _print_next_step(target_lang: str, connector: str, output_path: Path) -> None:
    config = LANG_NEXT_STEPS[target_lang]
    grace_dir = Path(__file__).resolve().parents[4]              # grace/ root
    target_repo = grace_dir.parent / config["target_repo"]       # sibling to grace/

    if not target_repo.exists():
        click.echo(f"\n⚠️  Target repo not found: {target_repo}")
        click.echo(f"   Tech spec written for --target-lang {target_lang}, but {config['target_repo']} is not present at the expected sibling path.")
        click.echo(f"   Either:")
        click.echo(f"     • Set up {config['target_repo']} as a sibling directory of grace/, OR")
        click.echo(f"     • Re-run with --target-lang <other> if you meant a different target.")
        return

    click.echo(f"\n✓ Tech spec written to {output_path}")
    click.echo(f"\nNext step (target language: {target_lang}):")
    click.echo(f"  Open {config['target_repo']} in your AI agent and run:")
    click.echo(f"    integrate {connector} using {config['rulesbook_path']}")

LANG_NEXT_STEPS = {
    "rust":   {"target_repo": "connector-service/",        "rulesbook_path": "grace/rulesbook/codegen-rust/.gracerules"},
    "python": {"target_repo": "lens/", "rulesbook_path": "grace/rulesbook/codegen-python/.gracerules"},
}
```

This converts what would be a silent failure (spec destined for a nonexistent repo) into a loud, actionable warning.

### 5.3 Tech-spec content is language-neutral

The spec describes the external PSP HTTP API. It does not vary with target language. No changes to tech-spec generation prompts are required for this design. (Wave 2 polish: `-e` enhancer may use `state["target_lang"]` to bias which sections it stresses.)

### 5.4 State schema additions

```python
class TechspecWorkflowState(TypedDict):
    target_lang: Literal["rust", "python"]   # NEW, required
    ...                                       # all existing fields unchanged
```

## 6. Python language pack contents

### 6.1 Entrypoints

| File | Invocation form (in external AI agent) |
|---|---|
| `.gracerules` | `integrate Razorpay using grace/rulesbook/codegen-python/.gracerules` |
| `.gracerules_add_flow` | `add Refund flow to Razorpay using grace/rulesbook/codegen-python/.gracerules_add_flow` |
| `.gracerules_add_payment_method` | `add UPI:Collect,Intent to Razorpay using grace/rulesbook/codegen-python/.gracerules_add_payment_method` |

Path-based disambiguation. No "in python" suffix in commands.

### 6.2 Wave 1 patterns (MVP, blocking)

Same set as before. **Ownership rule (NEW):** per-flow vs per-PM responsibility is now explicit.

| Pattern | File | Owns |
|---|---|---|
| Authorize (flow) | `guides/patterns/pattern_authorize.md` | Auth → HTTP call → response shape → status mapping. Generic; PM-agnostic body. |
| PSync (flow) | `guides/patterns/pattern_psync.md` | Status-query call, status-mapping. |
| Capture (flow) | `guides/patterns/pattern_capture.md` | Capture call, status update. |
| Refund (flow) | `guides/patterns/pattern_refund.md` | Refund call, status. |
| RSync (flow) | `guides/patterns/pattern_rsync.md` | Refund status query. |
| Void (flow) | `guides/patterns/pattern_void.md` | Void call, status. |
| IncomingWebhook (flow) | `guides/patterns/pattern_IncomingWebhook_flow.md` | Webhook signature verification, dedup, event-type routing, status update. |
| Card PM | `guides/patterns/authorize/card/pattern_authorize_card.md` | Card-specific request fields (PAN, CVV, expiry, name, billing) — feeds into Authorize. |
| Wallet PM | `guides/patterns/authorize/wallet/pattern_authorize_wallet.md` | Wallet token, wallet-type enum (`ApplePay`, `GooglePay`). |
| UPI PM | `guides/patterns/authorize/upi/pattern_authorize_upi.md` | Collect: VPA. Intent: redirect deep link. PSync polling vs webhook strategy. |

**Pattern body responsibility:** per-flow pattern files contain the *flow body skeleton* (transformer call, http.post, response parse, status map). Per-PM patterns contain the *payment-method-specific Pydantic models* and any PM-specific transformer logic. The flow body calls the PM transformer; PM patterns never make HTTP calls.

### 6.3 Wave 2 patterns (incremental, post-MVP)

Ported as connector demand arises:
- SetupMandate, RepeatPayment, MandateRevoke (UPI Autopay / eMandate — see Section 11 non-goal callout)
- CreateOrder, SessionToken, PaymentMethodToken
- DefendDispute, AcceptDispute, DSync
- IncrementalAuthorization, VoidPC
- Remaining PMs: BNPL, BankTransfer, BankDebit, BankRedirect, Crypto, GiftCard, MobilePayment, Reward

### 6.4 Pattern file structure

Each pattern file MUST contain the same six sections as Rust patterns:

1. 🎯 Quick Start (placeholders: `{ConnectorName}`, `{connector}`, `{base_url}`)
2. 📋 Prerequisites (sourced from `shared/flows.md`)
3. 🏗️ Modern Template
   - **Flow patterns**: full async method body with `@connector_flow` decorator, `_to_<flow>_request` and `_from_<flow>_response` transformer method stubs
   - **PM patterns**: Pydantic request models, PM-specific transformer logic to feed into the flow's request builder
4. 🔧 Legacy Manual Pattern (rarely needed in Python; only when decorator can't express the flow)
5. 🧪 Testing Strategy (pytest + httpx.AsyncClient against running FastAPI app, NOT against mocks)
6. ✅ Validation Checklist

### 6.5 Python type-system reference (`guides/types/types.md`)

Authoritative cross-reference between Rust UCS types and Python analogues. **`F` (flow) is intentionally not a type parameter on `PaymentData` in Python** — each flow has structurally distinct request/response types (e.g., `AuthorizeRequest` ≠ `CaptureRequest`), so the type system already disambiguates without a phantom `F` param. The `flow: Flow` runtime field on `PaymentData` is provided for logging and decorator dispatch.

| Rust (UCS) | Python equivalent | Notes |
|---|---|---|
| `RouterDataV2<F, Req, Resp>` | `PaymentData(BaseModel, Generic[Req, Resp])` with runtime `flow: Flow` field | Phantom `F` dropped intentionally — Req/Resp pair disambiguates each flow |
| `ConnectorIntegrationV2<F, Req, Resp>` | `BaseConnector(ABC)` with typed abstract methods per flow | See Section 7.3 |
| `macro_connector_implementation!` | `@connector_flow(flow=Flow.AUTHORIZE, ...)` decorator | See Section 7.4 — explicit kwargs, no introspection magic |
| `domain_types::*` | `from lens.domain_types import ...` | Shell-owned (Section 7) |
| `ConnectorError` | `lens.domain_types.errors.ConnectorError` with `retryable: bool`, `connector_status_code: Optional[str]` | |
| Status enums | `lens.domain_types.enums.{AttemptStatus, RefundStatus, ...}` | Same variants as Rust |
| `MinorUnit(i64)` | `Amount(BaseModel)` with `minor_units: int`, `currency: Currency` | Paise-native for INR |

### 6.6 Python-specific quality checks

See Section 8.4 — reworked to drop ABC-restated checks and add lifecycle / masking checks.

## 7. Python target service shape (`lens`)

### 7.1 Repository layout

```
lens/                 # NEW repo, sibling to grace/ and connector-service/
├── pyproject.toml                        # uv-managed; deps: fastapi, httpx, pydantic v2, uvicorn, structlog, pytest, mypy
├── lens/
│   ├── __init__.py
│   ├── domain_types/                     # Language-neutral domain models — the contract surface
│   │   ├── __init__.py                   # Re-exports everything codegen-python/guides/types/types.md names
│   │   ├── payment_data.py               # PaymentData[Req, Resp] + WebhookEvent
│   │   ├── flow_models.py                # AuthorizeRequest/Response, CaptureRequest/Response, etc. (one pair per flow)
│   │   ├── pm_models.py                  # CardData, WalletData, UpiData (Collect/Intent)
│   │   ├── enums.py                      # AttemptStatus, RefundStatus, Currency, Country, Flow, PaymentMethod, WalletType, UpiFlowType
│   │   ├── errors.py                     # ConnectorError hierarchy
│   │   ├── money.py                      # Amount, currency helpers (paise math, no floats)
│   │   └── masking.py                    # mask_vpa, mask_pan, mask_card — used by structlog processor
│   ├── connectors/                       # ← Grace generates files here
│   │   ├── __init__.py                   # Empty; per-connector __init__.py files register themselves
│   │   ├── _base.py                      # BaseConnector ABC + @connector_flow decorator + registry
│   │   ├── _registry.py                  # CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] + register/get helpers
│   │   ├── razorpay/
│   │   │   ├── __init__.py               # register_connector("razorpay", Razorpay)
│   │   │   ├── connector.py              # class Razorpay(BaseConnector)
│   │   │   ├── transformers.py           # Razorpay's request/response Pydantic models
│   │   │   └── auth.py                   # RazorpayAuth(BaseModel) — holds api_key + webhook_secret
│   │   └── ...
│   ├── api/                              # FastAPI app shell
│   │   ├── __init__.py
│   │   ├── server.py                     # FastAPI() + lifespan + router includes
│   │   ├── lifespan.py                   # @asynccontextmanager startup/shutdown — instantiates connectors, closes httpx clients
│   │   ├── routers/
│   │   │   ├── payments.py               # POST /v1/payments/{flow} → registry lookup → connector.<flow>()
│   │   │   └── webhooks.py               # POST /v1/webhooks/{connector} → registry lookup → connector.incoming_webhook()
│   │   └── middleware/
│   │       └── auth.py                   # API key validation
│   ├── observability/
│   │   ├── logging.py                    # structlog config; masking processor; std fields (request_id, connector, flow, latency_ms)
│   │   └── dedup.py                      # InMemoryDedupStore for webhook events; key = (connector, event_id)
│   └── schemas/                          # API-layer Pydantic schemas (wire types)
│       ├── payment.py                    # PaymentCreateRequest / PaymentResponse — API boundary; distinct from domain_types.flow_models
│       └── webhook.py
├── tests/
│   ├── conftest.py                       # pytest fixtures: live FastAPI app + httpx.AsyncClient
│   ├── contract/                         # Tests asserting types.md ↔ domain_types/ contract — see Section 12 risk
│   │   └── test_types_contract.py
│   ├── integration/                      # End-to-end against running app
│   │   └── test_razorpay.py              # Authorize + PSync + UPI Collect, etc.
│   └── unit/
├── scripts/
│   └── sync_creds.sh                     # cp ../connector-service/creds.json ./creds.json
└── creds.json                            # Copied from sibling connector-service/ via sync_creds.sh
```

### 7.2 Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Transport | **FastAPI (HTTP/REST)** | Python-idiomatic, auto-OpenAPI, debuggable with `curl`. Diverges from Rust UCS gRPC — accepted. |
| HTTP client (upstream) | **httpx.AsyncClient** | Modern, well-typed, HTTP/2, async. **One client per `BaseConnector` instance**, lifecycle managed by FastAPI `lifespan` (Section 7.5). |
| Models | **Pydantic v2** with `ConfigDict(extra="forbid")` | Strict — unknown PSP response fields raise. v2 perf adequate. |
| Async model | **All public connector methods `async def`** | High concurrency requirement. No sync escape hatches. |
| Type checking | **`mypy --strict` per-connector** (scoped, not whole package) | Quality gate; scoped to avoid drift between connectors blocking new ones. |
| Money | **`Amount(minor_units: int, currency: Currency)`** | Paise-native for INR. No float on money. |
| Auth | **Per-connector `*Auth(BaseModel)`** with `api_key` AND `webhook_secret` fields | Same key shape across `creds.json` entries. See Section 7.9. |
| Errors | **`ConnectorError(retryable: bool, connector_status_code: Optional[str], ...)`** | Routers translate to HTTP status codes via a single exception handler. |
| Logging | **structlog** with masking processor | See Section 7.7. PCI-aware: VPA / PAN / CVV / token. |
| Idempotency | **UUID4 from decorator unless overridden** via `PaymentData.idempotency_key` | See Section 7.8. |
| Webhook dedup | **In-memory store (Wave 1); Redis-backed (production / Wave 2)** | At-least-once UPI webhooks demand this from Wave 1. See Section 7.12. |

### 7.3 BaseConnector contract — concrete signatures

```python
# lens/connectors/_base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
import httpx
from pydantic import BaseModel

from lens.domain_types import (
    PaymentData, WebhookEvent,
    AuthorizeRequest, AuthorizeResponse,
    PSyncRequest, PSyncResponse,
    CaptureRequest, CaptureResponse,
    VoidRequest, VoidResponse,
    RefundRequest, RefundResponse,
    RSyncRequest, RSyncResponse,
)

Req = TypeVar("Req", bound=BaseModel)
Resp = TypeVar("Resp", bound=BaseModel)


class BaseAuth(BaseModel):
    """Subclassed per connector. Holds api_key + webhook_secret minimum."""
    api_key: str
    webhook_secret: str


class BaseConnector(ABC):
    """
    Stateless connector. One instance per (worker, connector) pair.
    httpx.AsyncClient is owned by this instance and closed by FastAPI lifespan.
    """
    name: str                       # class attribute, e.g. "razorpay"
    base_url: str                   # class attribute
    auth: BaseAuth                  # instance attribute
    client: httpx.AsyncClient       # instance attribute, opened in __aenter__, closed in __aexit__

    def __init__(self, auth: BaseAuth) -> None:
        self.auth = auth
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(30.0))

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.client.aclose()

    @abstractmethod
    async def authorize(
        self, data: PaymentData[AuthorizeRequest, AuthorizeResponse],
    ) -> PaymentData[AuthorizeRequest, AuthorizeResponse]: ...

    @abstractmethod
    async def psync(
        self, data: PaymentData[PSyncRequest, PSyncResponse],
    ) -> PaymentData[PSyncRequest, PSyncResponse]: ...

    @abstractmethod
    async def capture(
        self, data: PaymentData[CaptureRequest, CaptureResponse],
    ) -> PaymentData[CaptureRequest, CaptureResponse]: ...

    @abstractmethod
    async def void(
        self, data: PaymentData[VoidRequest, VoidResponse],
    ) -> PaymentData[VoidRequest, VoidResponse]: ...

    @abstractmethod
    async def refund(
        self, data: PaymentData[RefundRequest, RefundResponse],
    ) -> PaymentData[RefundRequest, RefundResponse]: ...

    @abstractmethod
    async def rsync(
        self, data: PaymentData[RSyncRequest, RSyncResponse],
    ) -> PaymentData[RSyncRequest, RSyncResponse]: ...

    @abstractmethod
    async def incoming_webhook(
        self, raw_payload: bytes, headers: dict[str, str],
    ) -> WebhookEvent: ...
```

`PaymentData` (Pydantic generic, declared properly):

```python
# lens/domain_types/payment_data.py
from pydantic import BaseModel, ConfigDict
from typing import Generic, TypeVar, Optional
from .enums import Flow, AttemptStatus

Req = TypeVar("Req", bound=BaseModel)
Resp = TypeVar("Resp", bound=BaseModel)


class PaymentData(BaseModel, Generic[Req, Resp]):
    model_config = ConfigDict(extra="forbid")

    flow: Flow                                 # runtime tag for logging/dispatch
    request: Req
    response: Optional[Resp] = None
    status: Optional[AttemptStatus] = None
    idempotency_key: Optional[str] = None      # caller may pre-set; decorator fills in if absent
    request_id: str                            # set by API layer (uuid4)
    connector_name: str
```

### 7.4 `@connector_flow` decorator — explicit contract

The decorator is **purely cross-cutting** — it does NOT do HTTP, transformer dispatch, or status mapping. Those live in the method body. The decorator wraps the body with:
1. Request logging (`request_id`, `connector_name`, `flow`, `latency_ms`)
2. Idempotency-key injection if absent (UUID4)
3. Error normalization: `httpx.HTTPStatusError` → `ConnectorError(retryable=False)`, `httpx.TimeoutException` → `ConnectorError(retryable=True)`, `pydantic.ValidationError` → `ConnectorError(retryable=False, message="parse failure: ...")`
4. Metric emission (latency histogram)

```python
# lens/connectors/_base.py
from functools import wraps
from time import monotonic
from uuid import uuid4
import httpx
from pydantic import ValidationError
import structlog

from lens.domain_types import Flow, ConnectorError

logger = structlog.get_logger()


def connector_flow(*, flow: Flow):
    """Cross-cutting wrapper. Does NOT do HTTP. Body owns transformer + http + status map."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, data):
            data.flow = flow
            data.idempotency_key = data.idempotency_key or str(uuid4())
            log = logger.bind(
                request_id=data.request_id,
                connector=data.connector_name,
                flow=flow.value,
                idempotency_key=data.idempotency_key,
            )
            start = monotonic()
            log.info("connector_flow.start")
            try:
                result = await fn(self, data)
            except httpx.TimeoutException as e:
                log.error("connector_flow.timeout", error=str(e))
                raise ConnectorError(retryable=True, message=f"timeout: {e}") from e
            except httpx.HTTPStatusError as e:
                log.error("connector_flow.http_error", status=e.response.status_code, body=e.response.text[:500])
                raise ConnectorError(
                    retryable=e.response.status_code >= 500,
                    connector_status_code=str(e.response.status_code),
                    message=f"http {e.response.status_code}: {e.response.text[:200]}",
                ) from e
            except ValidationError as e:
                log.error("connector_flow.parse_error", error=str(e))
                raise ConnectorError(retryable=False, message=f"parse failure: {e}") from e
            else:
                latency_ms = (monotonic() - start) * 1000
                log.info("connector_flow.done", status=result.status.value if result.status else None, latency_ms=latency_ms)
                return result
        return wrapper
    return decorator
```

**Worked Authorize example (the pattern in `pattern_authorize.md` produces code like this):**

```python
# lens/connectors/razorpay/connector.py
from lens.connectors._base import BaseConnector, connector_flow
from lens.connectors._registry import register_connector
from lens.domain_types import (
    PaymentData, AuthorizeRequest, AuthorizeResponse, Flow, AttemptStatus,
)
from .transformers import (
    RazorpayAuthorizeRequest, RazorpayAuthorizeResponse,
    to_authorize_request, from_authorize_response,
)
from .auth import RazorpayAuth


class Razorpay(BaseConnector):
    name = "razorpay"
    base_url = "https://api.razorpay.com/v1"

    @connector_flow(flow=Flow.AUTHORIZE)
    async def authorize(
        self, data: PaymentData[AuthorizeRequest, AuthorizeResponse],
    ) -> PaymentData[AuthorizeRequest, AuthorizeResponse]:
        request: RazorpayAuthorizeRequest = to_authorize_request(data.request)
        response = await self.client.post(
            "/payments/create",
            json=request.model_dump(by_alias=True),
            headers={
                **self._auth_headers(),
                "X-Razorpay-Idempotency": data.idempotency_key,
            },
        )
        response.raise_for_status()
        parsed = RazorpayAuthorizeResponse.model_validate_json(response.text)
        data.response = from_authorize_response(parsed)
        data.status = _map_status(parsed.status)
        return data

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth.api_key}"}

    # ... psync, capture, void, refund, rsync, incoming_webhook

register_connector("razorpay", Razorpay)


def _map_status(razorpay_status: str) -> AttemptStatus:
    return {
        "created":   AttemptStatus.PENDING,
        "captured":  AttemptStatus.CHARGED,
        "failed":    AttemptStatus.FAILURE,
        "authorized": AttemptStatus.AUTHORIZED,
    }[razorpay_status]
```

This concrete shape is what every Wave 1 pattern file produces.

### 7.5 Lifecycle: BaseConnector + httpx + FastAPI lifespan

httpx clients hold socket pools. Reuse is essential; leaks are real. The FastAPI lifespan owns the lifecycle:

```python
# lens/api/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from lens.connectors._registry import CONNECTOR_REGISTRY
from lens.domain_types.credentials import load_creds


@asynccontextmanager
async def lifespan(app: FastAPI):
    creds = load_creds("creds.json")
    instances: dict[str, "BaseConnector"] = {}
    for name, cls in CONNECTOR_REGISTRY.items():
        if name not in creds:
            continue
        auth = cls.AuthCls(**creds[name])    # each connector class declares AuthCls
        instances[name] = cls(auth=auth)
    app.state.connectors = instances
    try:
        yield
    finally:
        for inst in instances.values():
            await inst.client.aclose()
```

**Multi-worker note:** uvicorn `--workers N` forks; each worker owns its own `app.state.connectors`. Each connector has `N` `httpx.AsyncClient` instances total, one per worker. This is fine — httpx pools are bounded — and matches FastAPI's process-per-worker model.

### 7.6 Connector registry / dispatch

**Explicit registration**, not auto-import:

```python
# lens/connectors/_registry.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ._base import BaseConnector

CONNECTOR_REGISTRY: dict[str, type["BaseConnector"]] = {}


def register_connector(name: str, cls: type["BaseConnector"]) -> None:
    if name in CONNECTOR_REGISTRY:
        raise RuntimeError(f"Connector {name!r} already registered")
    CONNECTOR_REGISTRY[name] = cls


def get_connector(name: str, app_state) -> "BaseConnector":
    if name not in app_state.connectors:
        raise KeyError(f"Connector {name!r} not configured")
    return app_state.connectors[name]
```

Each connector's `__init__.py` calls `register_connector("razorpay", Razorpay)`. FastAPI dispatch:

```python
# lens/api/routers/payments.py
from fastapi import APIRouter, Request, HTTPException
from lens.connectors._registry import get_connector
from lens.schemas.payment import PaymentCreateRequest, PaymentResponse

router = APIRouter()


@router.post("/payments/{flow}", response_model=PaymentResponse)
async def payment(flow: str, body: PaymentCreateRequest, request: Request):
    connector = get_connector(body.connector_name, request.app.state)
    method = getattr(connector, flow, None)
    if method is None or flow not in {"authorize", "psync", "capture", "void", "refund", "rsync"}:
        raise HTTPException(404, f"Unknown flow {flow}")
    payment_data = body.to_payment_data(flow)        # API schema → domain PaymentData
    result = await method(payment_data)
    return PaymentResponse.from_payment_data(result) # domain PaymentData → API schema
```

The connectors `__init__.py` does NOT auto-import every connector — instead, the FastAPI app imports `lens.connectors.<name>` lazily on first use, or eagerly at startup based on what's in `creds.json`. Eager-at-startup is the Wave 1 default (in `lifespan`).

### 7.7 Logging & observability

**structlog** (consistent with Grace itself using structlog):

```python
# lens/observability/logging.py
import structlog
from lens.domain_types.masking import mask_vpa, mask_pan, mask_card_number


def mask_processor(_, __, event_dict):
    """structlog processor: redact PCI/PII fields before emission."""
    for sensitive in ("pan", "card_number", "cvv", "cvc"):
        if sensitive in event_dict:
            event_dict[sensitive] = mask_card_number(event_dict[sensitive]) if "card" in sensitive or "pan" in sensitive else "***"
    if "vpa" in event_dict:
        event_dict["vpa"] = mask_vpa(event_dict["vpa"])
    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        mask_processor,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

**Masking helpers** (`lens/domain_types/masking.py`):

```python
def mask_vpa(vpa: str) -> str:
    """alice@oksbi → al****@oksbi"""
    if "@" not in vpa: return "***"
    name, handle = vpa.split("@", 1)
    return (name[:2] + "*" * max(0, len(name) - 2)) + "@" + handle

def mask_card_number(pan: str) -> str:
    """4242424242424242 → 424242******4242"""
    digits = "".join(c for c in pan if c.isdigit())
    if len(digits) < 10: return "***"
    return digits[:6] + "*" * (len(digits) - 10) + digits[-4:]

def mask_pan(pan: str) -> str:
    """Indian PAN: ABCDE1234F → ABC****34F (or similar)"""
    if len(pan) < 8: return "***"
    return pan[:3] + "*" * (len(pan) - 6) + pan[-3:]
```

**Standard log fields** (emitted by `@connector_flow`):
- `request_id` (uuid4 from API layer)
- `connector` (connector name)
- `flow` (flow name)
- `idempotency_key`
- `latency_ms` (on completion)
- `status` (on completion, if mapped)
- `error_type` + `connector_status_code` (on failure)

### 7.8 Idempotency key generation

| Source | Behaviour |
|---|---|
| Caller-provided `PaymentData.idempotency_key` | Honored as-is. API layer surfaces this in `PaymentCreateRequest.idempotency_key` for callers who want at-least-once safety. |
| Caller omitted | `@connector_flow` decorator generates `uuid4()` and stores on `data.idempotency_key`. Visible to body. |
| Per-connector header name | Connector body sets the header explicitly (e.g., `"X-Razorpay-Idempotency": data.idempotency_key`). No magic — each connector knows its own PSP's header convention. |
| Retry semantics | Caller responsible. Server does NOT auto-retry; it just exposes `retryable: bool` on `ConnectorError`. |

### 7.9 Webhook signature verification + secret storage

`BaseAuth` (declared in 7.3) carries `api_key` AND `webhook_secret`. Both load from one `creds.json` entry per connector:

```json
// creds.json
{
  "razorpay": {
    "api_key": "rzp_test_...",
    "webhook_secret": "whsec_..."
  },
  "cashfree": {
    "api_key": "...",
    "webhook_secret": "..."
  }
}
```

Each connector implements `incoming_webhook` with signature verification before any business logic:

```python
async def incoming_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    received_sig = headers.get("x-razorpay-signature", "")
    expected_sig = hmac.new(
        self.auth.webhook_secret.encode(),
        raw_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_sig, expected_sig):
        raise ConnectorError(retryable=False, message="webhook signature mismatch")
    event = RazorpayWebhookEvent.model_validate_json(raw_payload)
    if await dedup_store.seen(self.name, event.id):
        return WebhookEvent.duplicate(event.id)
    await dedup_store.mark_seen(self.name, event.id)
    return _to_webhook_event(event)
```

Patterns enforce this skeleton (signature check → dedup → translate).

### 7.10 `creds.json` sharing mechanism

**One file per repo**, kept in sync via a checked-in script. Symlinks rejected (Windows compatibility, surprising for new contributors).

```bash
# lens/scripts/sync_creds.sh
#!/usr/bin/env bash
set -euo pipefail
SOURCE="../connector-service/creds.json"
DEST="./creds.json"
if [[ ! -f "$SOURCE" ]]; then
    echo "Source creds.json not found at $SOURCE" >&2
    exit 1
fi
cp "$SOURCE" "$DEST"
echo "✓ Copied $SOURCE → $DEST"
```

Schema is identical across repos. Both teams treat the same key-set as authoritative; schema changes require cross-team alignment (called out in `lens/README.md`).

### 7.11 UPI Intent redirection data

Authorize response for UPI Intent returns a deep link, not an HTTP redirect:

```python
# lens/domain_types/flow_models.py
from pydantic import BaseModel
from typing import Literal, Optional

class RedirectionData(BaseModel):
    method: Literal["GET", "POST", "INTENT"]    # INTENT = deep-link, no HTTP
    url: str                                     # e.g. "upi://pay?pa=merchant@oksbi&pn=...&am=100&tr=..."
    form_fields: Optional[dict[str, str]] = None

class AuthorizeResponse(BaseModel):
    connector_payment_id: str
    status: AttemptStatus
    redirection_data: Optional[RedirectionData] = None
    next_action: Optional["NextAction"] = None
    raw_response: dict                           # echo for debugging
```

UPI Collect does not use `redirection_data` — it returns `status: Pending` and the customer approves in the UPI app; status arrives via webhook (`incoming_webhook`) or PSync.

### 7.12 UPI webhook deduplication (Wave 1 constraint)

Razorpay/Cashfree webhooks deliver at-least-once. Without dedup, a "captured" event firing twice will double-count, double-charge metrics, or trigger double-refund. **Wave 1 ships an in-memory dedup store**; production deployments swap in a Redis-backed implementation in Wave 2.

```python
# lens/observability/dedup.py
from abc import ABC, abstractmethod
from collections import OrderedDict


class DedupStore(ABC):
    @abstractmethod
    async def seen(self, connector: str, event_id: str) -> bool: ...
    @abstractmethod
    async def mark_seen(self, connector: str, event_id: str) -> None: ...


class InMemoryDedupStore(DedupStore):
    """Per-process. Bounded LRU; sufficient for Wave 1 single-worker dev."""
    def __init__(self, max_size: int = 10_000) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._max = max_size

    async def seen(self, connector: str, event_id: str) -> bool:
        return f"{connector}:{event_id}" in self._seen

    async def mark_seen(self, connector: str, event_id: str) -> None:
        key = f"{connector}:{event_id}"
        self._seen[key] = None
        self._seen.move_to_end(key)
        if len(self._seen) > self._max:
            self._seen.popitem(last=False)
```

Single global instance bound at startup in `lifespan`. **Note for Wave 2:** the `DedupStore` interface is intentionally swappable so a Redis impl drops in without touching connector code.

### 7.13 transformers.py vs schemas/payment.py — boundary

| File | Type role | Direction | Owner |
|---|---|---|---|
| `lens/schemas/payment.py` | **Wire types** (HTTP API boundary) | API caller ↔ Grace service | Hand-written, stable, public contract |
| `lens/domain_types/flow_models.py` | **Domain types** (internal canonical) | API layer ↔ BaseConnector | Hand-written, stable, shared by all connectors |
| `lens/connectors/<name>/transformers.py` | **PSP-specific types + transformers** | BaseConnector body ↔ external PSP API | Grace-generated per connector |

Conversion happens twice per request: wire → domain (`PaymentCreateRequest.to_payment_data()`); domain → PSP (`to_authorize_request()` in transformers.py). The reverse runs on the response path.

Patterns generate `transformers.py`. They never modify `schemas/payment.py` or `flow_models.py`.

### 7.14 Bootstrap responsibility

`lens` is **hand-written once by a human** (mirroring the Rust UCS shell). Grace only generates per-connector files into `lens/connectors/<name>/`. No `grace bootstrap-service` subcommand.

## 8. Quality Guardian

### 8.1 Architecture

- Single shared scoring formula and threshold (`rulesbook/shared/quality_rubric.md`)
- Cross-cutting checks shared across languages (8.2)
- Language-specific check lists in each pack (8.3, 8.4)
- Each `.gracerules*` ends with a "Quality Review" section referencing both

### 8.2 Shared scoring formula and cross-cutting checks

**Formula (unchanged from current):**
```
Quality Score = 100 - (Critical × 20) - (Warnings × 5) - (Suggestions × 1)

95-100  Excellent — auto-approve
80-94   Good
60-79   Fair      ← threshold to proceed
40-59   Poor
0-39    Critical
```

**Cross-cutting checks (apply to all languages):**

| Check | Severity |
|---|---|
| Idempotency key sent on Authorize/Capture/Refund | Critical |
| Every documented PSP status mapped to a UCS status (no silent fallthrough to Failure) | Critical |
| No hardcoded secrets (auth only from Auth class/struct) | Critical |
| Coverage: every flow requested has a real implementation | Critical |
| Webhook signature verification present (if IncomingWebhook implemented) | Critical |
| Webhook dedup present (if IncomingWebhook implemented) — `DedupStore` consulted before processing | Critical |
| Currency/amount handling uses minor-unit-aware helpers; no float arithmetic | Critical |
| PCI/PII masking applied in any log line that touches PAN/CVV/VPA | Critical |
| Errors include connector-provided message + code | Warning |
| No fields hardcoded to None/null | Warning |
| No code duplication across flows | Suggestion |

### 8.3 Rust-specific checks (existing, preserved)

| Check | Severity |
|---|---|
| Uses `RouterDataV2`, not legacy `RouterData` | Critical |
| Uses `ConnectorIntegrationV2`, not legacy `ConnectorIntegration` | Critical |
| Imports from `domain_types::*`, not `hyperswitch_*` | Critical |
| Uses `macro_connector_implementation!` over manual traits | Warning |
| Generic connector struct: `pub struct ConnectorName<T> { phantom: PhantomData<T> }` | Critical |

### 8.4 Python-specific checks (reworked)

Dropped redundant checks restated from the ABC (those are enforced at import time, not by Quality Guardian).

| Check | Severity |
|---|---|
| `mypy --strict` clean on `lens/connectors/{connector}/` (scoped) | Critical |
| Pydantic models use `model_config = ConfigDict(extra="forbid")` | Critical |
| `@connector_flow` decorator present on every public flow method | Critical |
| `httpx.AsyncClient` is `self.client`, not constructed per call | Critical |
| `await self.client.aclose()` happens via `__aexit__` (not manually in body) | Warning |
| No bare `except:`; must catch specific exception types | Critical |
| No synchronous I/O in async paths (`requests`, `time.sleep`, `urllib.request` forbidden) | Critical |
| Decimal/int money only; no float in amount math | Critical |
| Uses `logging` / `structlog`, never `print()` | Warning |
| Logs touching PAN/CVV/VPA route through masking helpers | Critical |
| Domain types referenced from `lens.domain_types`, not stdlib `dict`/`list` | Warning |
| `register_connector(...)` called in `__init__.py` of the connector module | Critical — without it FastAPI never dispatches to it |

### 8.5 Feedback database

`rulesbook/shared/feedback.md` (moved from `codegen/guides/feedback.md`). Entries tagged `[lang:rust]`, `[lang:python]`, or `[lang:*]` (cross-cutting). The existing `rulesbook-pattern-auditor` agent ([.claude/agents/rulesbook-pattern-auditor.md](.claude/agents/rulesbook-pattern-auditor.md)) filters by language.

## 9. Workflow agent changes

### 9.1 `{LANG}` parameter threaded through orchestration

| Agent | Change |
|---|---|
| `1_orchestrator.md` | New required input `{LANG}` (`rust` or `python`). Passed to every spawned `2_connector.md`. |
| `2_connector.md` | Receives `{LANG}`. Threaded to subagents. Working directory: `connector-service/` if `rust`, `lens/` if `python`. |
| `2.1_links.md` | Unchanged. Link discovery is language-neutral. |
| `2.2_techspec.md` | `grace techspec {connector} --target-lang {LANG} ...` |
| `2.3_codegen.md` | Language config block at top; lang-aware build/test/rulesbook-path/commit-glob. |
| `2.4_pr.md` | PR title prefix: `[python]` / `[rust]`. Stage glob by language. |

### 9.2 Language config block in `2.3_codegen.md` (build command fixed)

```markdown
## Language config (selected by {LANG})

### rust
- repo: connector-service/
- build: cargo build
- test: grpcurl -d '{...}' -plaintext localhost:50051 PaymentService/Authorize
- service-start: cargo run --bin grpc-server
- rulesbook: grace/rulesbook/codegen-rust/
- glob: backend/connector-integration/src/connectors/{connector}*

### python
- repo: lens/
- build:
    uv run mypy lens/connectors/{connector}/ \
      && uv run pytest tests/integration/test_{connector}.py --collect-only
- test:
    uv run pytest tests/integration/test_{connector}.py::test_authorize -v \
      && uv run pytest tests/integration/test_{connector}.py::test_psync -v
- service-start: uv run uvicorn lens.api.server:app --port 8000
- rulesbook: grace/rulesbook/codegen-python/
- glob: lens/connectors/{connector}*
```

**Build fix details:** `mypy` is scoped to the new connector's directory (not the whole package — prevents drift in other connectors from blocking new ones). `pytest --collect-only` proves the test file imports cleanly and pytest can discover tests, without actually running them. Real test execution is the next step (`test:` line).

### 9.3 Hard rules carry over per-language

All existing guardrails from `1_orchestrator.md` apply equally to Python:
- Strictly sequential, never parallel
- Build → smoke test → commit is a hard gate
- No retries without code change
- Scoped git (no `-A`, no force push)
- Credentials from `creds.json`; missing entry = silently SKIPPED
- Fully autonomous; no questions to user mid-run

Python analogue of "no `cargo test`": **"no `pytest` against pure mocks — integration tests hit a running FastAPI app via `httpx.AsyncClient`."**

### 9.4 Branch naming

User-supplied `{BRANCH}` is used as-is. Cross-repo isolation (Rust → `connector-service/`, Python → `lens/`) prevents collision when branch names match across languages. PR titles are language-prefixed for cross-tool visibility.

## 10. Migration plan (PHASES REORDERED — shell-first)

The independent review caught that the original Phase 3 (write patterns) preceded Phase 5 (write the shell those patterns reference). The reorder below fixes that — patterns are now authored against real symbols.

### Phase 0 — Pre-work
- Sanity-check this design against repo state
- Verify `lens` repo can be created (org access, naming)
- Optional: fix the `enhacer.md ` trailing-space filename (touching it later fights this design)

### Phase 1 — Rename + extract shared spine (BREAKING externally; no external consumers per constraint)
- `git mv rulesbook/codegen rulesbook/codegen-rust`
- Create `rulesbook/shared/`
- Move with `git mv` (history preserved):
  - `codegen-rust/guides/feedback.md` → `shared/feedback.md` (tag existing entries `[lang:rust]`)
  - `codegen-rust/guides/learnings/learnings.md` → `shared/learnings.md`
  - `codegen-rust/connector_integration/template/tech_spec.md` → `shared/tech_spec_template.md`
- Extract from `codegen-rust/README.md`:
  - Flow definitions + prerequisite DAG → `shared/flows.md`
  - Payment-method category list → `shared/payment_methods.md`
  - Quality formula + cross-cutting checks → `shared/quality_rubric.md`
- Update internal references in `workflow/*.md`, `README.md`, `setup.md`, `CLAUDE.md`, `extract_source_urls_simple.sh`, `codegen-rust/add_connector.sh`
- Update path references INSIDE all `codegen-rust/.gracerules*` files — `s/codegen/codegen-rust/g` plus `s|guides/learnings/learnings.md|../shared/learnings.md|g`, `s|guides/feedback.md|../shared/feedback.md|g`
- Quality Guardian sections in `.gracerules*` updated to reference `shared/quality_rubric.md` for the formula
- **Acceptance gate:** generate a sample Rust connector before AND after Phase 1, then `diff -r` the generated output. Must be identical. This catches any silently broken path reference.

### Phase 2 — `grace techspec` CLI changes
- Add `-l/--target-lang` to `src/cli.py`, default `python`
- Thread through `run_techspec_workflow` → `TechspecWorkflow.execute` → `TechspecWorkflowState["target_lang"]`
- Add per-language next-step config dict in `src/workflows/techspec/nodes/output_node.py`
- Add target-repo-exists safety check (Section 5.2 — prints warning when sibling repo absent)
- Update CLAUDE.md, README.md, setup.md — loud callout that the default changed
- **Acceptance gate:** flag accepted; both lang values print correct next-step OR warning when target repo missing

### Phase 3 — Bootstrap `lens` shell (HAND-WRITTEN, MOVED EARLIER)

This was Phase 5 in the prior draft. Moved up because patterns (Phase 4) must reference real symbols.

- New repo `lens`
- Hand-write shell:
  - `lens/domain_types/` — `payment_data.py` (`PaymentData[Req, Resp]`), `flow_models.py` (all six flow Request/Response pairs), `pm_models.py` (Card/Wallet/UPI), `enums.py`, `errors.py`, `money.py`, `masking.py`
  - `lens/connectors/_base.py` — `BaseConnector` ABC + `@connector_flow` decorator
  - `lens/connectors/_registry.py` — registration + lookup
  - `lens/api/` — FastAPI app, routers/payments + routers/webhooks, lifespan, auth middleware
  - `lens/observability/` — structlog config + dedup store
  - `lens/schemas/` — API-layer Pydantic schemas
- `pyproject.toml` (uv): fastapi, httpx, pydantic v2, uvicorn, structlog, pytest, pytest-asyncio, mypy
- `creds.json` schema documented; `scripts/sync_creds.sh` written
- `tests/conftest.py` — pytest fixtures for live FastAPI + httpx client
- `tests/contract/test_types_contract.py` — asserts every symbol named in `codegen-python/guides/types/types.md` is importable from `lens.domain_types` (catches drift)
- `mypy --strict lens/` clean on the empty shell
- **Acceptance gate:** `uvicorn` starts, `/health` returns 200, `mypy --strict` clean, contract test passes (empty success — no connectors yet, but the type names check)

### Phase 4 — Python language pack — Wave 1 (depends on Phase 3 symbols)
- Create `rulesbook/codegen-python/` directory shape
- Write `codegen-python/guides/types/types.md` referencing real symbols from Phase 3
- Write Wave 1 pattern files (7 flows + 3 PMs, with UPI Collect + Intent split)
- Write `codegen-python/.gracerules*` triad
- Write `codegen-python/guides/quality/` Python-specific checks
- Run `rulesbook-pattern-auditor` agent on every new pattern file — must pass
- Update [CLAUDE.md](CLAUDE.md) and the [add-connector-pattern](.claude/skills/add-connector-pattern/SKILL.md), [grace-workflow-node](.claude/skills/grace-workflow-node/SKILL.md) skills
- **Acceptance gate:** pattern auditor passes for all Wave 1 files; contract test from Phase 3 still passes (catches any rulesbook drift from shell types)

### Phase 5 — Workflow agent updates
- Add `{LANG}` to `1_orchestrator.md`, `2_connector.md`
- Add language config block to `2.3_codegen.md` (Section 9.2)
- `2.2_techspec.md`: pass `--target-lang {LANG}` to grace
- `2.4_pr.md`: lang-prefixed titles, lang-specific glob
- **Acceptance gate:** orchestrator with `{LANG}=python` against a 1-connector list produces a Python connector end-to-end (combined with Phase 6)

### Phase 6 — End-to-end MVP validation (Razorpay)
- `grace techspec razorpay -f ./razorpay-docs/ --target-lang python -e -v`
- `techspec-reviewer` agent → READY
- AI agent in `lens/` → `integrate Razorpay using grace/rulesbook/codegen-python/.gracerules`
- Quality Guardian score ≥ 60
- `mypy --strict lens/connectors/razorpay/` clean
- `pytest tests/integration/test_razorpay.py` passes for Authorize + PSync + UPI Collect + IncomingWebhook (signature + dedup)
- Contract test (Phase 3) still passes
- PRs created by `2.4_pr.md`
- Lessons logged to `rulesbook/shared/feedback.md` with `[lang:python]` tag
- **Acceptance gate = MVP DONE**

### Phase 7 — Wave 2 (incremental)
Port remaining flow patterns and PMs as connector demand arises. Pattern-auditor on each. Includes UPI Autopay (SetupMandate + RepeatPayment + MandateRevoke). Also: Redis-backed dedup store implementing the `DedupStore` interface from Phase 3.

## 11. Out of scope / explicit non-goals

- **Plugin schema** (Approach C): deferred unless a 4th language is added. Approach A can evolve into it.
- **TypeScript language pack:** planned but not designed here.
- **Auto-generation of `lens` shell:** explicitly rejected. Hand-written, one-time.
- **Tech-spec content language-awareness:** rejected. Spec is language-neutral by construction.
- **Migration of existing Rust connectors:** no changes. Rust output remains identical.
- **UPI Autopay / eMandate (SetupMandate + RepeatPayment + MandateRevoke):** Wave 2 only. Surfaced explicitly because "UPI" in Indian merchant conversations often implies recurring; this design's Wave 1 deliberately does not include it.
- **Production-grade dedup store (Redis-backed):** Wave 2. Wave 1 ships in-memory.
- **Cross-lang code-generation comparison agents:** not needed. Each lang's Quality Guardian is sufficient.

## 12. Open risks

1. **`enhacer.md ` filename has a trailing space** and is referenced by string in `src/workflows/techspec/nodes/enhance_spec.py`. If fixed, do it in Phase 0 — touching it later fights this design.
2. **The Rust `.gracerules` file is ~60kB** of carefully prompt-engineered content. Phase 1 path updates inside it must be exact — wrong paths cause silent fallthrough. **Mitigation:** Phase 1's `diff -r` acceptance gate catches this concretely.
3. **`creds.json` shared schema** requires cross-team coordination on schema changes between Rust UCS and Python service teams. Documented in `lens/README.md`.
4. **FastAPI vs Rust gRPC divergence** means the two services do not share a `.proto`. Each has its own contract. Accepted trade-off.
5. **Defaulting `--target-lang` to `python`** is a strategic statement. Mitigation: target-repo-exists warning (Section 5.2) converts silent failure to loud warning.
6. **`codegen-python/guides/types/types.md` ↔ `lens/lens/domain_types/` contract drift.** Most fragile coupling. **Mitigation promoted to ACCEPTANCE GATE:** `tests/contract/test_types_contract.py` in Phase 3 imports every symbol named in the rulesbook's types.md from `lens.domain_types` and fails CI on drift. The contract test re-runs in Phase 4 (with patterns) and Phase 6 (with a real connector).
7. **In-memory dedup store does not survive worker restarts.** A UPI webhook arriving twice across a deploy may double-process. **Mitigation:** documented as Wave 1 constraint; Wave 2 ships Redis-backed `DedupStore` impl behind the same interface.
8. **httpx default timeout of 30s** is too aggressive for some Indian PSPs under load. **Mitigation:** per-connector override via `httpx.Timeout(...)` configured in the connector class; pattern files surface this as a TODO in `__init__`.
9. **PCI logging via masking processor** only protects fields that have been explicitly named. New PSPs that ship novel sensitive field names (e.g., "card_pin") will bypass masking until the masker is updated. **Mitigation:** Quality Guardian Critical check enforces logging routes through masking helpers for any known PCI/PII field name.

## 13. Success criteria

- Phase 1 lands without changing Rust output (`diff -r` acceptance gate clean)
- Phase 3 ships with `mypy --strict` clean and contract test passing
- A Wave 1 Python pattern file passes the `rulesbook-pattern-auditor` agent
- One Indian connector (Razorpay) implemented end-to-end in Python via Grace with Quality score ≥ 60
- `mypy --strict` clean (scoped) on generated code
- Integration tests for Authorize + PSync + UPI Collect + IncomingWebhook (signature + dedup) pass against a running FastAPI app
- A PR for the work is created by `2.4_pr.md` with `[python]` prefix
- Contract test continues to pass after Phase 6

## 14. Affected files

**Renamed:**
- `rulesbook/codegen/` → `rulesbook/codegen-rust/`

**New directories:**
- `rulesbook/shared/`
- `rulesbook/codegen-python/`
- `rulesbook/codegen-python/guides/patterns/`
- `rulesbook/codegen-python/guides/patterns/authorize/{card,wallet,upi}/`
- `rulesbook/codegen-python/guides/types/`
- `rulesbook/codegen-python/guides/quality/`
- `docs/superpowers/specs/` (where this doc lives)

**New files (in this repo):**
- `rulesbook/shared/flows.md`, `payment_methods.md`, `quality_rubric.md`
- `rulesbook/codegen-python/.gracerules`, `.gracerules_add_flow`, `.gracerules_add_payment_method`
- `rulesbook/codegen-python/guides/types/types.md`
- 10 Wave 1 pattern files (7 flows + 3 PMs)
- Python-specific quality check files in `rulesbook/codegen-python/guides/quality/`

**Modified files (in this repo):**
- `src/cli.py` — new `--target-lang` option
- `src/workflows/__init__.py` — pass `target_lang` through
- `src/workflows/techspec/workflow.py` — `target_lang` on initial state
- `src/workflows/techspec/states/techspec_state.py` — add `target_lang` field
- `src/workflows/techspec/nodes/output_node.py` — per-lang next-step config + target-repo-exists warning
- `workflow/1_orchestrator.md`, `2_connector.md`, `2.2_techspec.md`, `2.3_codegen.md`, `2.4_pr.md`
- `README.md`, `setup.md`, `CLAUDE.md`
- `extract_source_urls_simple.sh`, `codegen-rust/add_connector.sh` (paths only)
- All `.gracerules*` files in `codegen-rust/` — internal path references to moved guides

**Moved files (with `git mv`):**
- `codegen-rust/guides/feedback.md` → `shared/feedback.md`
- `codegen-rust/guides/learnings/learnings.md` → `shared/learnings.md`
- `codegen-rust/connector_integration/template/tech_spec.md` → `shared/tech_spec_template.md`

**External repo (separate effort, tracked in Phase 3):**
- `lens/` — entire new repo. Layout in Section 7.1. Approximately 25 source files at MVP including:
  - `lens/domain_types/` (8 files: `payment_data.py`, `flow_models.py`, `pm_models.py`, `enums.py`, `errors.py`, `money.py`, `masking.py`, `credentials.py`)
  - `lens/connectors/_base.py`, `_registry.py`
  - `lens/api/` (server, lifespan, 2 routers, auth middleware = 5 files)
  - `lens/observability/` (logging, dedup = 2 files)
  - `lens/schemas/` (payment, webhook = 2 files)
  - `tests/conftest.py`, `tests/contract/test_types_contract.py`
  - `scripts/sync_creds.sh`
  - `pyproject.toml`, `README.md`

---

*End of design (revised).*
