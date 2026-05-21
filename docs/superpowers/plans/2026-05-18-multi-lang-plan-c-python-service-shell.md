# Multi-Lang Connector Generation — Plan C: Bootstrap `lens`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hand-write the Python connector-service shell at `/Users/sarthak/PycharmProjects/symplora/lens/`, mirroring (in Python/FastAPI) what `connector-service/` does for Rust. After Plan C lands, `uvicorn` starts the app, `/health` returns 200, `mypy --strict` is clean, and a contract test asserts the type-system surface matches what Plan D's pattern pack will import.

**Architecture:** FastAPI + httpx.AsyncClient + Pydantic v2. `BaseConnector` ABC + `@connector_flow` decorator + explicit `register_connector(name, cls)` registry. Per-connector `connectors/<name>/` directories will be filled later by Plan D's codegen — Plan C only provides the empty shell. Tests for now are a single contract test that imports every symbol Plan D's `codegen-python/guides/types/types.md` will name, proving the surface exists.

**Tech Stack:** Python 3.10+, FastAPI, httpx, Pydantic v2, uvicorn, structlog, pytest, mypy. uv-managed `pyproject.toml`.

**Source spec:** [docs/superpowers/specs/2026-05-18-multi-lang-connector-generation-design.md](../specs/2026-05-18-multi-lang-connector-generation-design.md) Section 7 (Python target service shape).

**Depends on:** Plans A + B (rulesbook + CLI/workflow), both landed on `python-support` branch in the grace repo.

**Repo location:** `/Users/sarthak/PycharmProjects/symplora/lens/` (new repo, sibling of `grace/`).

---

## Working directory note

Plan C operates ENTIRELY in the new repo `/Users/sarthak/PycharmProjects/symplora/lens/`. Do NOT modify anything in `/Users/sarthak/PycharmProjects/symplora/grace/`. The plan file itself lives in grace's `docs/superpowers/plans/` for archival, but all task work touches the new repo only.

The new repo gets its OWN git init and its own commit chain (starts at zero). Use `main` as the default branch; this is the first version.

---

## File structure (target layout)

```
lens/
├── .gitignore
├── pyproject.toml
├── README.md
├── creds.json                              # Sample / empty schema
├── scripts/
│   └── sync_creds.sh
├── lens/
│   ├── __init__.py
│   ├── domain_types/
│   │   ├── __init__.py                     # Re-exports everything
│   │   ├── enums.py                        # AttemptStatus, RefundStatus, Currency, Country, Flow, PaymentMethod, WalletType, UpiFlowType
│   │   ├── money.py                        # Amount(BaseModel)
│   │   ├── errors.py                       # ConnectorError + subclasses
│   │   ├── masking.py                      # mask_vpa, mask_pan, mask_card_number
│   │   ├── payment_data.py                 # PaymentData[Req, Resp] generic + WebhookEvent
│   │   ├── flow_models.py                  # Per-flow Request/Response Pydantic models (6 pairs)
│   │   ├── pm_models.py                    # CardData, WalletData, UpiData
│   │   └── credentials.py                  # BaseAuth + load_creds()
│   ├── connectors/
│   │   ├── __init__.py                     # Empty (each connector's __init__ self-registers)
│   │   ├── _base.py                        # BaseConnector ABC + @connector_flow decorator
│   │   └── _registry.py                    # CONNECTOR_REGISTRY + register_connector + get_connector
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── logging.py                      # structlog config + masking processor
│   │   └── dedup.py                        # DedupStore ABC + InMemoryDedupStore
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── payment.py                      # API-layer Pydantic schemas
│   │   └── webhook.py
│   └── api/
│       ├── __init__.py
│       ├── server.py                       # FastAPI() + lifespan + router includes + /health
│       ├── lifespan.py                     # asynccontextmanager — instantiates connectors, closes clients
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── payments.py                 # POST /v1/payments/{flow}
│       │   └── webhooks.py                 # POST /v1/webhooks/{connector}
│       └── middleware/
│           ├── __init__.py
│           └── auth.py                     # API key validation
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── contract/
    │   ├── __init__.py
    │   └── test_types_contract.py          # Imports everything Plan D will name
    ├── integration/                        # Empty for now
    └── unit/                               # Empty for now
```

---

## Tasks

### Task 1: Project init + pyproject.toml + .gitignore + git init

**Working directory:** Create `/Users/sarthak/PycharmProjects/symplora/lens/` and operate inside it.

**Files to create:**
- `pyproject.toml`
- `.gitignore`

- [ ] **Step 1: Create the repo directory**

```bash
mkdir -p /Users/sarthak/PycharmProjects/symplora/lens
cd /Users/sarthak/PycharmProjects/symplora/lens
pwd  # confirm
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lens"
version = "0.1.0"
description = "Python connector service for Symplora's payment integration platform"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Symplora" }]
dependencies = [
    "fastapi>=0.110.0",
    "httpx>=0.27.0",
    "pydantic>=2.5.0",
    "uvicorn[standard]>=0.27.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
    "httpx>=0.27.0",  # also used by tests for AsyncClient
]

[tool.setuptools]
packages = ["lens"]
include-package-data = true

[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_ignores = true
warn_redundant_casts = true
no_implicit_optional = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true

[[tool.mypy.overrides]]
module = "structlog.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Write `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.Python
.venv/
venv/
build/
dist/

# Type-checking
.mypy_cache/

# Testing
.pytest_cache/
htmlcov/
.coverage

# Editor
.vscode/
.idea/

# OS
.DS_Store

# Local config
.env
creds.json
!creds.json.example
```

- [ ] **Step 4: Write a minimal `README.md`** (will be expanded in Task 11)

```markdown
# lens

Python implementation of Symplora's payment connector service. Sibling
of `connector-service/` (Rust) and `grace/` (codegen toolkit).

Bootstrapped from grace's Plan C — see grace/docs/superpowers/specs/.

## Quick start

```bash
uv sync
uv run uvicorn lens.api.server:app --reload
curl http://localhost:8000/health
```

See "Acceptance gates" in Plan C for the full bring-up sequence.
```

- [ ] **Step 5: git init + initial commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
git init -b main
git add pyproject.toml .gitignore README.md
git commit -m "chore: initial bootstrap of lens

Empty scaffold per grace Plan C. Subsequent commits add domain types,
connector base, FastAPI app, and contract tests."
```

- [ ] **Step 6: Verify**

```bash
ls -la
git log --oneline
```
Expected: 3 files visible; one initial commit.

---

### Task 2: `lens/domain_types/` foundational types

**Working dir:** `/Users/sarthak/PycharmProjects/symplora/lens/`

**Files to create:** All under `lens/domain_types/`. These 4 files are pure-data — no cross-references among each other.

- [ ] **Step 1: Create the package skeleton**

```bash
mkdir -p lens/domain_types
touch lens/__init__.py
```

- [ ] **Step 2: Write `lens/domain_types/enums.py`**

```python
"""Domain enums — language-neutral, used by every flow and payment method."""

from enum import Enum


class Flow(str, Enum):
    AUTHORIZE = "authorize"
    PSYNC = "psync"
    CAPTURE = "capture"
    VOID = "void"
    REFUND = "refund"
    RSYNC = "rsync"
    INCOMING_WEBHOOK = "incoming_webhook"


class AttemptStatus(str, Enum):
    STARTED = "started"
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CHARGED = "charged"
    CAPTURED = "captured"
    AUTHORIZATION_FAILED = "authorization_failed"
    FAILURE = "failure"
    VOIDED = "voided"
    PARTIAL_CHARGED = "partial_charged"
    PAYMENT_METHOD_AWAITED = "payment_method_awaited"
    CONFIRMATION_AWAITED = "confirmation_awaited"
    DEVICE_DATA_COLLECTION_PENDING = "device_data_collection_pending"


class RefundStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    TRANSACTION_FAILURE = "transaction_failure"
    MANUAL_REVIEW = "manual_review"


class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AUD = "AUD"
    SGD = "SGD"
    # Additional currencies added per connector demand.


class Country(str, Enum):
    IN = "IN"
    US = "US"
    GB = "GB"
    AU = "AU"
    SG = "SG"


class PaymentMethod(str, Enum):
    CARD = "card"
    WALLET = "wallet"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    BANK_DEBIT = "bank_debit"
    BANK_REDIRECT = "bank_redirect"
    BNPL = "bnpl"
    CRYPTO = "crypto"
    GIFT_CARD = "gift_card"
    MOBILE_PAYMENT = "mobile_payment"
    REWARD = "reward"


class WalletType(str, Enum):
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    PAYPAL = "paypal"
    SAMSUNG_PAY = "samsung_pay"
    PAYTM = "paytm"
    PHONEPE = "phonepe"


class UpiFlowType(str, Enum):
    COLLECT = "collect"
    INTENT = "intent"
```

- [ ] **Step 3: Write `lens/domain_types/money.py`**

```python
"""Money type — minor-units integer, never floats on monetary values."""

from pydantic import BaseModel, ConfigDict, Field

from .enums import Currency


class Amount(BaseModel):
    """A monetary amount.

    minor_units: integer in the currency's minor unit (paise for INR, cents for USD).
    currency: ISO 4217 currency code via the Currency enum.

    Float arithmetic on amounts is FORBIDDEN — always operate on minor_units (int).
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    minor_units: int = Field(..., ge=0, description="Amount in minor currency units (paise/cents)")
    currency: Currency
```

- [ ] **Step 4: Write `lens/domain_types/errors.py`**

```python
"""Error hierarchy — every connector failure normalizes through ConnectorError."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConnectorError(Exception):
    """Base exception for connector failures.

    Carries retryability hint and the connector-provided status code (if any).
    The API layer translates this into appropriate HTTP responses.
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        connector_status_code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.connector_status_code = connector_status_code

    def __repr__(self) -> str:
        return (
            f"ConnectorError(message={self.message!r}, "
            f"retryable={self.retryable}, "
            f"connector_status_code={self.connector_status_code!r})"
        )


class ValidationError(ConnectorError):
    """Request payload failed validation before reaching the upstream PSP."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class AuthenticationError(ConnectorError):
    """PSP rejected our credentials (HTTP 401/403, signature mismatch, etc)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class UpstreamTimeoutError(ConnectorError):
    """PSP did not respond in time. Retryable."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class ErrorResponse(BaseModel):
    """API-layer representation of a ConnectorError (for HTTP body)."""
    model_config = ConfigDict(extra="forbid")

    message: str
    retryable: bool
    connector_status_code: Optional[str] = None
```

- [ ] **Step 5: Write `lens/domain_types/masking.py`**

```python
"""PCI/PII masking helpers — applied by structlog processors and any direct log lines."""


def mask_vpa(vpa: str) -> str:
    """Mask a UPI VPA: 'alice@oksbi' -> 'al****@oksbi'."""
    if not vpa or "@" not in vpa:
        return "***"
    name, handle = vpa.split("@", 1)
    if not name:
        return "***@" + handle
    visible = name[:2]
    return visible + "*" * max(0, len(name) - 2) + "@" + handle


def mask_card_number(pan: str) -> str:
    """Mask a card PAN: '4242424242424242' -> '424242******4242'."""
    digits = "".join(c for c in pan if c.isdigit())
    if len(digits) < 10:
        return "***"
    return digits[:6] + "*" * (len(digits) - 10) + digits[-4:]


def mask_pan(pan: str) -> str:
    """Mask an Indian PAN: 'ABCDE1234F' -> 'ABC****34F'."""
    if not pan or len(pan) < 8:
        return "***"
    return pan[:3] + "*" * (len(pan) - 6) + pan[-3:]
```

- [ ] **Step 6: Commit**

```bash
git add lens/
git commit -m "feat(domain_types): add foundational types (enums, money, errors, masking)

Pure-data layer with no inter-references. Enums cover the flow/PM/status
surface; Amount enforces minor-unit integers; ConnectorError carries
retryability hints; masking helpers cover VPA/PAN/card."
```

- [ ] **Step 7: Verify**

```bash
python -c "from lens.domain_types.enums import Flow, AttemptStatus, Currency, PaymentMethod, UpiFlowType; from lens.domain_types.money import Amount; from lens.domain_types.errors import ConnectorError, ValidationError; from lens.domain_types.masking import mask_vpa, mask_pan, mask_card_number; print('OK')"
```
Expected: `OK`. (You may need to `uv venv && source .venv/bin/activate && uv pip install -e .` first if running from a fresh repo.)

---

### Task 3: `lens/domain_types/` composite types

**Files to create:** `payment_data.py`, `flow_models.py`, `pm_models.py`, `credentials.py`, `__init__.py`.

- [ ] **Step 1: Write `lens/domain_types/payment_data.py`**

```python
"""PaymentData — the universal envelope passed to every connector method."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .enums import AttemptStatus, Flow

Req = TypeVar("Req", bound=BaseModel)
Resp = TypeVar("Resp", bound=BaseModel)


class PaymentData(BaseModel, Generic[Req, Resp]):
    """Generic envelope. Each flow parameterizes (Req, Resp) with its own pair.

    The runtime `flow` field is the AI-readable tag for logging/dispatch — it is
    NOT used as a type parameter because the (Req, Resp) pair already disambiguates.
    """
    model_config = ConfigDict(extra="forbid")

    flow: Flow
    request: Req
    response: Optional[Resp] = None
    status: Optional[AttemptStatus] = None
    idempotency_key: Optional[str] = None
    request_id: str
    connector_name: str


class WebhookEvent(BaseModel):
    """Parsed/normalized webhook event from a connector."""
    model_config = ConfigDict(extra="forbid")

    connector_name: str
    event_id: str
    event_type: str
    is_duplicate: bool = False
    payload: dict = Field(default_factory=dict)

    @classmethod
    def duplicate(cls, connector_name: str, event_id: str) -> "WebhookEvent":
        return cls(
            connector_name=connector_name,
            event_id=event_id,
            event_type="duplicate",
            is_duplicate=True,
            payload={},
        )
```

- [ ] **Step 2: Write `lens/domain_types/pm_models.py`**

```python
"""Payment-method-specific data classes — referenced by flow request models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from .enums import UpiFlowType, WalletType


class CardData(BaseModel):
    """Card payment input."""
    model_config = ConfigDict(extra="forbid")

    card_number: str
    card_exp_month: str
    card_exp_year: str
    card_holder_name: str
    card_cvc: str
    card_issuer: Optional[str] = None


class WalletData(BaseModel):
    """Wallet payment input."""
    model_config = ConfigDict(extra="forbid")

    wallet_type: WalletType
    token: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UpiData(BaseModel):
    """UPI payment input. Collect vs Intent driven by upi_flow."""
    model_config = ConfigDict(extra="forbid")

    upi_flow: UpiFlowType
    vpa: Optional[str] = None  # required for Collect, optional for Intent
```

- [ ] **Step 3: Write `lens/domain_types/flow_models.py`**

```python
"""Per-flow request/response models.

One pair per flow. Imported by BaseConnector's abstract method signatures.
"""

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict

from .enums import AttemptStatus, RefundStatus
from .money import Amount
from .pm_models import CardData, UpiData, WalletData

PaymentMethodInput = Union[CardData, WalletData, UpiData]


class CustomerData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None


class RedirectionData(BaseModel):
    """Authorize response side-channel: where the customer is redirected next.

    method=INTENT means the URL is a deep link (e.g., `upi://pay?...`) for app
    handoff. method=GET/POST means a browser redirect.
    """
    model_config = ConfigDict(extra="forbid")
    method: Literal["GET", "POST", "INTENT"]
    url: str
    form_fields: Optional[dict[str, str]] = None


# ---- Authorize ----

class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Amount
    payment_method: PaymentMethodInput
    customer: Optional[CustomerData] = None
    return_url: Optional[str] = None
    capture_method: Literal["automatic", "manual"] = "automatic"
    metadata: dict[str, str] = {}


class AuthorizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    status: AttemptStatus
    redirection_data: Optional[RedirectionData] = None
    raw_response: dict = {}


# ---- PSync ----

class PSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str


class PSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    status: AttemptStatus
    amount_received: Optional[Amount] = None
    raw_response: dict = {}


# ---- Capture ----

class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    amount_to_capture: Amount


class CaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    status: AttemptStatus
    amount_captured: Amount
    raw_response: dict = {}


# ---- Void ----

class VoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    cancellation_reason: Optional[str] = None


class VoidResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    status: AttemptStatus
    raw_response: dict = {}


# ---- Refund ----

class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_payment_id: str
    refund_amount: Amount
    refund_reason: Optional[str] = None


class RefundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_refund_id: str
    status: RefundStatus
    refund_amount: Amount
    raw_response: dict = {}


# ---- RSync ----

class RSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_refund_id: str


class RSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_refund_id: str
    status: RefundStatus
    raw_response: dict = {}
```

- [ ] **Step 4: Write `lens/domain_types/credentials.py`**

```python
"""Credential storage — `creds.json` shape and BaseAuth model.

`creds.json` is one entry per connector, e.g.:

    {
      "razorpay": {"api_key": "rzp_test_...", "webhook_secret": "whsec_..."},
      "cashfree": {"api_key": "...", "webhook_secret": "..."}
    }

Each connector subclass may extend BaseAuth with additional required fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseAuth(BaseModel):
    """Bare-minimum authentication shape. Subclassed per connector if needed."""
    model_config = ConfigDict(extra="allow")  # allow per-connector extensions

    api_key: str
    webhook_secret: Optional[str] = None


def load_creds(path: str | Path = "creds.json") -> dict[str, dict[str, str]]:
    """Load credentials dict from JSON file. Returns {} if file is absent."""
    p = Path(path)
    if not p.exists():
        return {}
    with p.open() as f:
        data: dict[str, dict[str, str]] = json.load(f)
    return data
```

- [ ] **Step 5: Write `lens/domain_types/__init__.py`**

Re-export everything so callers can do `from lens.domain_types import ...`:

```python
"""Public surface of domain_types.

Plan D's `codegen-python/guides/types/types.md` will reference these names —
keep them stable.
"""

from .credentials import BaseAuth, load_creds
from .enums import (
    AttemptStatus,
    Country,
    Currency,
    Flow,
    PaymentMethod,
    RefundStatus,
    UpiFlowType,
    WalletType,
)
from .errors import (
    AuthenticationError,
    ConnectorError,
    ErrorResponse,
    UpstreamTimeoutError,
    ValidationError,
)
from .flow_models import (
    AuthorizeRequest,
    AuthorizeResponse,
    CaptureRequest,
    CaptureResponse,
    CustomerData,
    PaymentMethodInput,
    PSyncRequest,
    PSyncResponse,
    RedirectionData,
    RefundRequest,
    RefundResponse,
    RSyncRequest,
    RSyncResponse,
    VoidRequest,
    VoidResponse,
)
from .masking import mask_card_number, mask_pan, mask_vpa
from .money import Amount
from .payment_data import PaymentData, WebhookEvent
from .pm_models import CardData, UpiData, WalletData

__all__ = [
    # enums
    "Flow", "AttemptStatus", "RefundStatus", "Currency", "Country",
    "PaymentMethod", "WalletType", "UpiFlowType",
    # money / errors / masking
    "Amount",
    "ConnectorError", "ValidationError", "AuthenticationError",
    "UpstreamTimeoutError", "ErrorResponse",
    "mask_vpa", "mask_pan", "mask_card_number",
    # composite
    "PaymentData", "WebhookEvent",
    "CardData", "WalletData", "UpiData",
    "AuthorizeRequest", "AuthorizeResponse",
    "PSyncRequest", "PSyncResponse",
    "CaptureRequest", "CaptureResponse",
    "VoidRequest", "VoidResponse",
    "RefundRequest", "RefundResponse",
    "RSyncRequest", "RSyncResponse",
    "CustomerData", "RedirectionData", "PaymentMethodInput",
    # credentials
    "BaseAuth", "load_creds",
]
```

- [ ] **Step 6: Verify imports**

```bash
python -c "from lens.domain_types import *; print('OK')"
```
Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add lens/domain_types/
git commit -m "feat(domain_types): add composite types (PaymentData, flow models, PMs, credentials)

Per-flow Request/Response pairs (Authorize/PSync/Capture/Void/Refund/RSync),
PM data classes (CardData, WalletData, UpiData), credential loader, and
__init__.py re-exporting the full public surface."
```

---

### Task 4: `lens/connectors/` base + registry

**Files:** `connectors/__init__.py`, `connectors/_registry.py`, `connectors/_base.py`.

- [ ] **Step 1: Create the package**

```bash
mkdir -p lens/connectors
touch lens/connectors/__init__.py
```

The `__init__.py` stays empty — per-connector packages will self-register via `register_connector(...)` in their own `__init__.py` (Plan D).

- [ ] **Step 2: Write `lens/connectors/_registry.py`**

```python
"""Connector registry. Each connector's `__init__.py` calls register_connector(...)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._base import BaseConnector

CONNECTOR_REGISTRY: dict[str, type["BaseConnector"]] = {}


def register_connector(name: str, cls: type["BaseConnector"]) -> None:
    """Register a connector class under a lowercase name.

    Raises RuntimeError on duplicate registration to catch typos / import-order bugs.
    """
    if name in CONNECTOR_REGISTRY:
        raise RuntimeError(f"Connector {name!r} already registered")
    CONNECTOR_REGISTRY[name] = cls


def get_connector_instance(name: str, app_state: Any) -> "BaseConnector":
    """Look up an instantiated connector from FastAPI app.state.connectors.

    Raises KeyError if the connector isn't in app.state.connectors — typically
    means the connector has no creds.json entry.
    """
    instances: dict[str, "BaseConnector"] = getattr(app_state, "connectors", {})
    if name not in instances:
        raise KeyError(f"Connector {name!r} is not configured (missing creds?)")
    return instances[name]
```

- [ ] **Step 3: Write `lens/connectors/_base.py`**

```python
"""BaseConnector ABC + @connector_flow decorator.

BaseConnector defines the contract every PSP integration implements. The
decorator wraps each flow method with cross-cutting concerns (logging,
idempotency-key generation, error normalization) — but it does NOT do HTTP
or transformer dispatch; that's the body's job.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import wraps
from time import monotonic
from typing import Any, Callable, Coroutine, TypeVar
from uuid import uuid4

import httpx
import structlog
from pydantic import ValidationError as PydanticValidationError

from lens.domain_types import (
    AuthorizeRequest, AuthorizeResponse,
    BaseAuth,
    CaptureRequest, CaptureResponse,
    ConnectorError, UpstreamTimeoutError, ValidationError,
    Flow,
    PaymentData,
    PSyncRequest, PSyncResponse,
    RefundRequest, RefundResponse,
    RSyncRequest, RSyncResponse,
    VoidRequest, VoidResponse,
    WebhookEvent,
)

logger = structlog.get_logger()

T = TypeVar("T")


def connector_flow(*, flow: Flow) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]],
    Callable[..., Coroutine[Any, Any, T]],
]:
    """Decorator for connector flow methods.

    Wraps the body with:
      - Structured logging (request_id, connector, flow, latency_ms)
      - Idempotency-key injection (uuid4 if absent)
      - Error normalization (httpx + Pydantic → ConnectorError subclasses)

    The decorated method's body owns transformers, HTTP calls, and status mapping.
    """
    def decorator(fn: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(fn)
        async def wrapper(self: "BaseConnector", data: PaymentData[Any, Any]) -> T:
            data.flow = flow
            if not data.idempotency_key:
                data.idempotency_key = str(uuid4())

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
                raise UpstreamTimeoutError(f"timeout: {e}") from e
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response is not None else 0
                body_preview = e.response.text[:500] if e.response is not None else ""
                log.error("connector_flow.http_error", status=status_code, body=body_preview)
                raise ConnectorError(
                    f"http {status_code}: {body_preview[:200]}",
                    retryable=status_code >= 500,
                    connector_status_code=str(status_code),
                ) from e
            except PydanticValidationError as e:
                log.error("connector_flow.parse_error", error=str(e))
                raise ValidationError(f"parse failure: {e}") from e
            else:
                latency_ms = (monotonic() - start) * 1000
                log.info("connector_flow.done", latency_ms=latency_ms)
                return result
        return wrapper
    return decorator


class BaseConnector(ABC):
    """Abstract base class. Per-PSP subclasses implement each flow method.

    Each subclass overrides class attributes `name`, `base_url`, and defines
    a `*Auth` class (subclass of BaseAuth). Subclasses must use the
    @connector_flow(flow=Flow.<NAME>) decorator on every flow method.
    """
    name: str = ""
    base_url: str = ""
    AuthCls: type[BaseAuth] = BaseAuth

    def __init__(self, auth: BaseAuth) -> None:
        if not self.name:
            raise RuntimeError(f"{type(self).__name__}.name must be set")
        if not self.base_url:
            raise RuntimeError(f"{type(self).__name__}.base_url must be set")
        self.auth = auth
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
        )

    async def aclose(self) -> None:
        """Close the underlying httpx client. Called by FastAPI lifespan on shutdown."""
        await self.client.aclose()

    @abstractmethod
    async def authorize(
        self, data: PaymentData[AuthorizeRequest, AuthorizeResponse],
    ) -> PaymentData[AuthorizeRequest, AuthorizeResponse]:
        ...

    @abstractmethod
    async def psync(
        self, data: PaymentData[PSyncRequest, PSyncResponse],
    ) -> PaymentData[PSyncRequest, PSyncResponse]:
        ...

    @abstractmethod
    async def capture(
        self, data: PaymentData[CaptureRequest, CaptureResponse],
    ) -> PaymentData[CaptureRequest, CaptureResponse]:
        ...

    @abstractmethod
    async def void(
        self, data: PaymentData[VoidRequest, VoidResponse],
    ) -> PaymentData[VoidRequest, VoidResponse]:
        ...

    @abstractmethod
    async def refund(
        self, data: PaymentData[RefundRequest, RefundResponse],
    ) -> PaymentData[RefundRequest, RefundResponse]:
        ...

    @abstractmethod
    async def rsync(
        self, data: PaymentData[RSyncRequest, RSyncResponse],
    ) -> PaymentData[RSyncRequest, RSyncResponse]:
        ...

    @abstractmethod
    async def incoming_webhook(
        self, raw_payload: bytes, headers: dict[str, str],
    ) -> WebhookEvent:
        ...
```

- [ ] **Step 4: Verify**

```bash
python -c "from lens.connectors._base import BaseConnector, connector_flow; from lens.connectors._registry import register_connector, CONNECTOR_REGISTRY; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add lens/connectors/
git commit -m "feat(connectors): add BaseConnector ABC, @connector_flow decorator, registry

BaseConnector defines the 6 core flow abstract methods + incoming_webhook.
@connector_flow handles cross-cutting concerns (logging, idempotency key,
error normalization). _registry holds the name→class map; each connector's
__init__.py will call register_connector(...) when Plan D's codegen produces it."
```

---

### Task 5: `lens/observability/`

**Files:** `observability/__init__.py`, `observability/logging.py`, `observability/dedup.py`.

- [ ] **Step 1: Create the package**

```bash
mkdir -p lens/observability
touch lens/observability/__init__.py
```

- [ ] **Step 2: Write `lens/observability/logging.py`**

```python
"""structlog configuration + PCI/PII masking processor."""

from __future__ import annotations

from typing import Any

import structlog

from lens.domain_types.masking import mask_card_number, mask_pan, mask_vpa


def mask_processor(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """structlog processor: redact PCI/PII fields before emission."""
    for sensitive in ("pan", "card_number", "card_pan"):
        if sensitive in event_dict:
            event_dict[sensitive] = mask_card_number(str(event_dict[sensitive]))
    for cvv_key in ("cvv", "cvc", "card_cvc"):
        if cvv_key in event_dict:
            event_dict[cvv_key] = "***"
    if "vpa" in event_dict:
        event_dict["vpa"] = mask_vpa(str(event_dict["vpa"]))
    if "indian_pan" in event_dict:
        event_dict["indian_pan"] = mask_pan(str(event_dict["indian_pan"]))
    return event_dict


def configure_logging() -> None:
    """Idempotent structlog setup. Call from FastAPI lifespan startup."""
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

- [ ] **Step 3: Write `lens/observability/dedup.py`**

```python
"""Webhook deduplication store.

UPI webhooks (Razorpay/Cashfree) deliver at-least-once. Without dedup, the
same 'captured' event can fire twice and double-charge metrics/refunds.

Wave 1: in-memory bounded LRU. Wave 2: Redis-backed implementation behind
the same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict


class DedupStore(ABC):
    @abstractmethod
    async def seen(self, connector: str, event_id: str) -> bool: ...

    @abstractmethod
    async def mark_seen(self, connector: str, event_id: str) -> None: ...


class InMemoryDedupStore(DedupStore):
    """Per-process bounded LRU. Single-worker dev only — does NOT survive restarts.

    Plan E acceptance gate requires this works for Razorpay UPI Collect webhook
    integration test. Production deployments swap in a Redis-backed impl.
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._max = max_size

    def _key(self, connector: str, event_id: str) -> str:
        return f"{connector}:{event_id}"

    async def seen(self, connector: str, event_id: str) -> bool:
        return self._key(connector, event_id) in self._seen

    async def mark_seen(self, connector: str, event_id: str) -> None:
        key = self._key(connector, event_id)
        self._seen[key] = None
        self._seen.move_to_end(key)
        if len(self._seen) > self._max:
            self._seen.popitem(last=False)
```

- [ ] **Step 4: Write `observability/__init__.py`** (re-exports)

```python
from .dedup import DedupStore, InMemoryDedupStore
from .logging import configure_logging, mask_processor

__all__ = ["DedupStore", "InMemoryDedupStore", "configure_logging", "mask_processor"]
```

- [ ] **Step 5: Verify**

```bash
python -c "from lens.observability import configure_logging, InMemoryDedupStore; configure_logging(); print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add lens/observability/
git commit -m "feat(observability): structlog config + masking + InMemoryDedupStore

mask_processor redacts PAN/CVV/VPA/indian_pan before any log emission.
InMemoryDedupStore is bounded-LRU for at-least-once webhook deduplication;
Wave 2 will provide a Redis-backed implementation behind the same interface."
```

---

### Task 6: `lens/schemas/` (API wire types)

**Files:** `schemas/__init__.py`, `schemas/payment.py`, `schemas/webhook.py`.

- [ ] **Step 1: Create the package**

```bash
mkdir -p lens/schemas
touch lens/schemas/__init__.py
```

- [ ] **Step 2: Write `lens/schemas/payment.py`**

```python
"""API-layer payment schemas. Wire types distinct from domain types.

Keeps the FastAPI surface decoupled from internal connector model evolution.
"""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict

from lens.domain_types.flow_models import (
    AuthorizeRequest,
    CaptureRequest,
    PSyncRequest,
    RefundRequest,
    RSyncRequest,
    VoidRequest,
)

FlowRequest = Union[
    AuthorizeRequest,
    PSyncRequest,
    CaptureRequest,
    VoidRequest,
    RefundRequest,
    RSyncRequest,
]


class PaymentCreateRequest(BaseModel):
    """Incoming API payload for any flow."""
    model_config = ConfigDict(extra="forbid")

    connector_name: str
    request_id: str
    idempotency_key: Optional[str] = None
    request: FlowRequest


class PaymentResponse(BaseModel):
    """Outgoing API payload. The shape mirrors the inbound flow's response shape
    plus the universal payment-data fields.
    """
    model_config = ConfigDict(extra="allow")  # connector-specific response keys vary

    connector_name: str
    request_id: str
    status: Optional[str] = None
    response: dict
```

- [ ] **Step 3: Write `lens/schemas/webhook.py`**

```python
"""Webhook API-layer schema."""

from pydantic import BaseModel, ConfigDict


class WebhookAck(BaseModel):
    """Generic webhook acknowledgement response."""
    model_config = ConfigDict(extra="forbid")

    received: bool = True
    duplicate: bool = False
    event_id: str
```

- [ ] **Step 4: Write `schemas/__init__.py`**

```python
from .payment import PaymentCreateRequest, PaymentResponse, FlowRequest
from .webhook import WebhookAck

__all__ = ["PaymentCreateRequest", "PaymentResponse", "FlowRequest", "WebhookAck"]
```

- [ ] **Step 5: Commit**

```bash
git add lens/schemas/
git commit -m "feat(schemas): API-layer Pydantic wire types

PaymentCreateRequest envelopes per-flow Request types; PaymentResponse is
the outbound shape. Webhook ack carries duplicate flag for at-least-once
delivery handling."
```

---

### Task 7: `lens/api/` — middleware + routers + lifespan + server

**Files:** `api/__init__.py`, `api/middleware/__init__.py`, `api/middleware/auth.py`, `api/routers/__init__.py`, `api/routers/payments.py`, `api/routers/webhooks.py`, `api/lifespan.py`, `api/server.py`.

- [ ] **Step 1: Create the package shape**

```bash
mkdir -p lens/api/middleware lens/api/routers
touch lens/api/__init__.py
touch lens/api/middleware/__init__.py
touch lens/api/routers/__init__.py
```

- [ ] **Step 2: Write `lens/api/middleware/auth.py`**

```python
"""API-key authentication middleware. Stub for Wave 1 — accepts any key."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status


async def api_key_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Verify an Authorization header is present.

    Wave 1: any non-empty Bearer token is accepted. Hardening (signature
    verification, scoped API keys, rate limiting) lands in Wave 2.

    The /health endpoint is skipped — it must be reachable without auth.
    """
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return await call_next(request)
```

- [ ] **Step 3: Write `lens/api/routers/payments.py`**

```python
"""Payments router. POST /v1/payments/{flow} dispatches to the named connector."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status

from lens.connectors._registry import get_connector_instance
from lens.domain_types import (
    AttemptStatus,
    PaymentData,
)
from lens.domain_types.errors import ConnectorError
from lens.schemas.payment import PaymentCreateRequest, PaymentResponse

router = APIRouter(prefix="/v1/payments", tags=["payments"])

FlowName = Literal["authorize", "psync", "capture", "void", "refund", "rsync"]


@router.post("/{flow}", response_model=PaymentResponse)
async def payment(
    flow: FlowName, body: PaymentCreateRequest, request: Request
) -> PaymentResponse:
    """Route a payment request to the named connector's flow method."""
    try:
        connector = get_connector_instance(body.connector_name, request.app.state)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    method = getattr(connector, flow, None)
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown flow: {flow}"
        )

    payment_data: PaymentData = PaymentData(
        flow=connector.__class__.__name__,  # decorator overrides this
        request=body.request,
        request_id=body.request_id,
        connector_name=body.connector_name,
        idempotency_key=body.idempotency_key,
    )

    try:
        result = await method(payment_data)
    except ConnectorError as e:
        http_status = (
            status.HTTP_502_BAD_GATEWAY if e.retryable else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=http_status,
            detail={
                "message": e.message,
                "retryable": e.retryable,
                "connector_status_code": e.connector_status_code,
            },
        ) from e

    response_payload = (
        result.response.model_dump() if result.response is not None else {}
    )
    return PaymentResponse(
        connector_name=result.connector_name,
        request_id=result.request_id,
        status=result.status.value if isinstance(result.status, AttemptStatus) else None,
        response=response_payload,
    )
```

- [ ] **Step 4: Write `lens/api/routers/webhooks.py`**

```python
"""Webhooks router. POST /v1/webhooks/{connector} forwards to the connector's handler."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from lens.connectors._registry import get_connector_instance
from lens.domain_types.errors import ConnectorError
from lens.schemas.webhook import WebhookAck

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/{connector}", response_model=WebhookAck)
async def incoming_webhook(connector: str, request: Request) -> WebhookAck:
    """Receive a webhook for the named connector, verify signature, dedup, normalize."""
    try:
        instance = get_connector_instance(connector, request.app.state)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    raw_payload = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    try:
        event = await instance.incoming_webhook(raw_payload, headers)
    except ConnectorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": e.message, "retryable": e.retryable},
        ) from e

    return WebhookAck(
        received=True,
        duplicate=event.is_duplicate,
        event_id=event.event_id,
    )
```

- [ ] **Step 5: Write `lens/api/lifespan.py`**

```python
"""FastAPI lifespan: instantiates connectors at startup, closes clients at shutdown."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI

from lens.connectors._registry import CONNECTOR_REGISTRY
from lens.domain_types import load_creds
from lens.observability.dedup import InMemoryDedupStore
from lens.observability.logging import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: configure logging, load creds, instantiate registered connectors.

    Shutdown: close every connector's httpx client.
    """
    configure_logging()
    creds = load_creds("creds.json")

    instances: dict[str, object] = {}
    for name, cls in CONNECTOR_REGISTRY.items():
        if name not in creds:
            logger.warning("connector_skipped_no_creds", connector=name)
            continue
        auth = cls.AuthCls(**creds[name])
        instances[name] = cls(auth=auth)
        logger.info("connector_instantiated", connector=name)

    app.state.connectors = instances
    app.state.dedup_store = InMemoryDedupStore()

    logger.info("lifespan.startup_complete", connector_count=len(instances))
    try:
        yield
    finally:
        for name, inst in instances.items():
            aclose = getattr(inst, "aclose", None)
            if aclose is not None:
                await aclose()
                logger.info("connector_closed", connector=name)
```

- [ ] **Step 6: Write `lens/api/server.py`**

```python
"""FastAPI app factory + /health endpoint."""

from __future__ import annotations

from fastapi import FastAPI

from lens.api.lifespan import lifespan
from lens.api.middleware.auth import api_key_middleware
from lens.api.routers import payments, webhooks


def create_app() -> FastAPI:
    """Build the FastAPI application instance."""
    app = FastAPI(
        title="lens",
        description="Symplora payment connector service (Python edition)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.middleware("http")(api_key_middleware)
    app.include_router(payments.router)
    app.include_router(webhooks.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 7: Verify**

```bash
python -c "from lens.api.server import app; print('OK', type(app).__name__)"
```
Expected: `OK FastAPI`.

- [ ] **Step 8: Commit**

```bash
git add lens/api/
git commit -m "feat(api): FastAPI app with payments + webhooks routers + lifespan

POST /v1/payments/{flow} dispatches to named connector's flow method via
registry. POST /v1/webhooks/{connector} verifies+dedups+normalizes events.
Lifespan instantiates connectors from creds.json at startup, closes their
httpx clients at shutdown. /health is unauthenticated; everything else
requires a Bearer token (validation stubbed for Wave 1)."
```

---

### Task 8: `scripts/sync_creds.sh` + `creds.json` sample

**Files:** `scripts/sync_creds.sh`, `creds.json`.

- [ ] **Step 1: Write `scripts/sync_creds.sh`**

```bash
mkdir -p scripts
```

Then create the script with this content:

```bash
#!/usr/bin/env bash
# Sync creds.json from the sibling connector-service/ repo.
#
# The Rust UCS and Python services share credential storage. This script
# copies the canonical creds.json from connector-service/ to here.
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

Make it executable:
```bash
chmod +x scripts/sync_creds.sh
```

- [ ] **Step 2: Write `creds.json` (empty sample)**

Create `creds.json` with empty contents:

```json
{}
```

This file is gitignored — it's only here so `load_creds("creds.json")` returns `{}` on a fresh checkout without crashing.

- [ ] **Step 3: Commit**

```bash
git add scripts/sync_creds.sh
# creds.json is gitignored; do NOT add it
git status --short  # confirm only sync_creds.sh shows as staged
git commit -m "feat(scripts): add sync_creds.sh for cross-repo credential sync

creds.json is gitignored. Run scripts/sync_creds.sh to copy from
../connector-service/creds.json which is the shared source of truth."
```

---

### Task 9: Tests — conftest + contract test

**Files:** `tests/__init__.py`, `tests/conftest.py`, `tests/contract/__init__.py`, `tests/contract/test_types_contract.py`.

- [ ] **Step 1: Create the test package shape**

```bash
mkdir -p tests/contract tests/integration tests/unit
touch tests/__init__.py
touch tests/contract/__init__.py
touch tests/integration/__init__.py
touch tests/unit/__init__.py
```

- [ ] **Step 2: Write `tests/conftest.py`**

```python
"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from lens.api.server import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous FastAPI test client. Auth bypass is the responsibility of the test."""
    return TestClient(app)
```

- [ ] **Step 3: Write `tests/contract/test_types_contract.py`**

This is the acceptance gate test the design spec promotes from a risk-mitigation note to a hard gate. It imports every symbol that Plan D's `codegen-python/guides/types/types.md` will reference from `lens.domain_types`. If the rulesbook ever drifts from the shell, this test fails.

```python
"""Contract test: types.md ↔ domain_types/ surface.

The Plan D rulesbook (`grace/rulesbook/codegen-python/guides/types/types.md`)
names types that generated connectors will import. If a name listed in the
rulesbook is missing from `lens.domain_types`, codegen produces
import-failure connectors.

This test pins the public surface. When the rulesbook is updated to introduce
new types, update this test in the same PR.
"""

import pytest


def test_all_public_types_importable() -> None:
    """Every symbol the rulesbook names must be importable from lens.domain_types."""
    from lens.domain_types import (
        # Enums
        AttemptStatus,
        Country,
        Currency,
        Flow,
        PaymentMethod,
        RefundStatus,
        UpiFlowType,
        WalletType,
        # Money / errors / masking
        Amount,
        AuthenticationError,
        ConnectorError,
        ErrorResponse,
        UpstreamTimeoutError,
        ValidationError,
        mask_card_number,
        mask_pan,
        mask_vpa,
        # Composite
        AuthorizeRequest,
        AuthorizeResponse,
        CaptureRequest,
        CaptureResponse,
        CardData,
        CustomerData,
        PaymentData,
        PaymentMethodInput,
        PSyncRequest,
        PSyncResponse,
        RedirectionData,
        RefundRequest,
        RefundResponse,
        RSyncRequest,
        RSyncResponse,
        UpiData,
        VoidRequest,
        VoidResponse,
        WalletData,
        WebhookEvent,
        # Credentials
        BaseAuth,
        load_creds,
    )
    # If imports succeed, the contract holds.
    assert ConnectorError is not None
    assert PaymentData is not None
    assert Amount(minor_units=100, currency=Currency.INR).minor_units == 100


def test_baseconnector_abstract_methods_exist() -> None:
    """BaseConnector must expose every flow method the rulesbook decorates."""
    from lens.connectors._base import BaseConnector

    expected = {"authorize", "psync", "capture", "void", "refund", "rsync", "incoming_webhook"}
    actual = set(BaseConnector.__abstractmethods__)
    missing = expected - actual
    assert not missing, f"BaseConnector missing abstract methods: {missing}"


def test_connector_flow_decorator_importable() -> None:
    """The @connector_flow decorator must be importable from connectors._base."""
    from lens.connectors._base import connector_flow
    from lens.domain_types import Flow

    decorator = connector_flow(flow=Flow.AUTHORIZE)
    assert callable(decorator)


def test_registry_helpers_present() -> None:
    """Registry must expose register_connector and CONNECTOR_REGISTRY."""
    from lens.connectors._registry import CONNECTOR_REGISTRY, register_connector

    assert isinstance(CONNECTOR_REGISTRY, dict)
    assert callable(register_connector)


def test_health_endpoint_returns_200(client: "TestClient") -> None:
    """/health is the smoke-test acceptance gate."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Note:** The `client` fixture type annotation uses a forward-reference string `"TestClient"` so the test file imports cleanly even before `TestClient` is in scope at the top. Pytest resolves this at runtime.

- [ ] **Step 4: Install dependencies and run tests**

```bash
# Set up venv if not already
if [[ ! -d .venv ]]; then
    uv venv
fi
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```
Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: add contract test pinning types.md ↔ domain_types surface

5 tests:
- All public types importable from lens.domain_types
- BaseConnector abstract methods cover every flow
- @connector_flow decorator and registry helpers present
- /health endpoint returns 200

These together are the Plan C acceptance gate."
```

---

### Task 10: Acceptance gate — install, mypy --strict, uvicorn boot, health 200

**This is verification-only. No new files.**

- [ ] **Step 1: mypy --strict on the whole package**

```bash
source .venv/bin/activate
uv pip install mypy
uv run mypy lens/
```
Expected: `Success: no issues found in N source files`. Fix any reported issues by adjusting type annotations (NOT by adding `# type: ignore` unless a third-party stub is genuinely missing).

- [ ] **Step 2: All tests pass**

```bash
pytest tests/ -v
```
Expected: all 5 tests pass.

- [ ] **Step 3: uvicorn boots**

In a background terminal (or with `&`):
```bash
uv run uvicorn lens.api.server:app --port 8000 &
sleep 2
```

Then:
```bash
curl -i http://localhost:8000/health
```
Expected: `HTTP/1.1 200 OK` and body `{"status":"ok"}`.

Stop the server:
```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 4: Verify /v1/payments rejects no-auth requests**

Re-boot uvicorn (same as Step 3), then:
```bash
curl -i http://localhost:8000/v1/payments/authorize -X POST -d '{}'
```
Expected: `HTTP/1.1 401 Unauthorized`.

Stop the server.

- [ ] **Step 5: Document the acceptance gate result**

If all four sub-steps pass — Plan C is structurally complete. Note this in the final commit message or PR description.

- [ ] **Step 6: No commit** (Acceptance gate is verification, not new code.)

---

### Task 11: Final README + commit chain check

**File:** `README.md` (expanded from the minimal stub).

- [ ] **Step 1: Replace `README.md` content with a fuller version**

```markdown
# lens

FastAPI-based Python implementation of Symplora's payment connector service.
Sibling of:
- `connector-service/` — Rust implementation (UCS)
- `grace/` — codegen toolkit and rulesbook

## Architecture

Per-PSP connectors implement `BaseConnector` (see `lens/connectors/_base.py`).
Each subclass is decorated by `@connector_flow(flow=Flow.<NAME>)` on every flow method,
which handles cross-cutting concerns (logging, idempotency keys, error normalization)
while the body owns the connector-specific logic (transformers, HTTP, status mapping).

Connectors register themselves via `register_connector("psp_name", PspClass)` in their
own `connectors/<name>/__init__.py`. The FastAPI app instantiates registered
connectors at startup from `creds.json` and closes their httpx clients on shutdown.

```
HTTP request
  ↓
api/middleware/auth.py     # Bearer token check (stub in Wave 1)
  ↓
api/routers/payments.py    # POST /v1/payments/{flow}
  ↓
connectors._registry       # lookup PspClass by name
  ↓
PspClass.{flow}            # @connector_flow wraps logging/error normalization
  ↓
PSP HTTP API (via httpx.AsyncClient)
```

## Quick start

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Sync credentials from the Rust UCS sibling repo
./scripts/sync_creds.sh

# Type-check
uv run mypy lens/

# Tests
pytest tests/ -v

# Run
uv run uvicorn lens.api.server:app --reload --port 8000
curl http://localhost:8000/health
```

## Layout

- `lens/domain_types/` — language-neutral domain models (PaymentData, flow Request/Response, PMs, enums, errors, money, masking)
- `lens/connectors/` — BaseConnector + registry; per-PSP packages added by grace's Plan D codegen
- `lens/api/` — FastAPI app (server, routers, lifespan, middleware)
- `lens/observability/` — structlog config + InMemoryDedupStore
- `lens/schemas/` — API-layer Pydantic wire types
- `tests/contract/` — pins the types.md ↔ domain_types surface
- `tests/integration/` — Plan E adds Razorpay end-to-end tests here

## What's missing (by design)

- Per-PSP connectors → Plan D (`grace/rulesbook/codegen-python/`)
- Razorpay end-to-end → Plan E
- Production-grade dedup (Redis) → Wave 2
- API key validation (real, not stub) → Wave 2
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: expand README with architecture, quick-start, and layout"
```

- [ ] **Step 3: Final state check**

```bash
ls -la
find . -type f -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.pytest_cache/*" -not -path "./__pycache__/*" -not -path "*/__pycache__/*" -not -path "./lens.egg-info/*" | sort
git log --oneline
```

Expect: ~24 files (excluding venv, caches, egg-info), ~10 commits, clean working tree.

---

## Plan C acceptance summary

The plan is done when:
- `mypy --strict lens/` is clean
- `pytest tests/` passes (5 tests)
- `uvicorn` starts; `curl http://localhost:8000/health` returns 200 with `{"status":"ok"}`
- `/v1/payments/authorize` without `Authorization: Bearer ...` returns 401
- `git status` is clean

After Plan C lands:
- Plan D can begin authoring `rulesbook/codegen-python/` patterns against real symbols
- Plan E (Razorpay E2E) waits on both Plan D AND Plan C
- The `output_node` next-step hint in grace (Plan B) will switch from warning to success when `lens/` exists at the sibling location

---

## Self-review notes (for the plan-writer)

Spec coverage:
- ✓ Section 7.1 layout — Tasks 1, 2-9
- ✓ Section 7.2 architectural decisions — embedded in each task's files
- ✓ Section 7.3 BaseConnector contract — Task 4
- ✓ Section 7.4 @connector_flow — Task 4
- ✓ Section 7.5 lifecycle — Task 7 lifespan
- ✓ Section 7.6 registry — Task 4
- ✓ Section 7.7 observability — Task 5
- ✓ Section 7.8 idempotency keys — Task 4 (in @connector_flow)
- ✓ Section 7.9 webhook secrets — Task 3 (in BaseAuth)
- ✓ Section 7.10 creds.json sharing — Task 8
- ✓ Section 7.11 UPI Intent redirection_data — Task 3 (flow_models.py)
- ✓ Section 7.12 dedup — Task 5
- ✓ Section 7.13 transformers vs schemas boundary — Task 6
- ✓ Phase 3 acceptance gate — Task 10
- ✓ Risk #6 (contract drift) — Task 9 contract test

Placeholders: none — every step has concrete file content or commands.

Type consistency: enums.py is the single source for Flow / status / currency / payment-method names; payment_data.py / flow_models.py / pm_models.py all import from enums.py; BaseConnector imports the flow Request/Response pairs from `lens.domain_types` (which re-exports them). No name collisions.
