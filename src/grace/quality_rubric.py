from __future__ import annotations

import ast
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from grace.pipeline.gates import MypyReport, PytestReport
from grace.pipeline.marker import has_marker
from grace.pipeline.types import GenerationContext


@dataclass(frozen=True)
class Dimension:
    name: str
    max: int
    score: int
    detail: str
    findings: list[str] = field(default_factory=list)
    """Per-item breakdown of what this dimension found. `detail` is a one-line
    summary; `findings` is the full list (e.g. every mypy error line, every
    failing pytest case). Empty for binary-pass dimensions or when there's
    nothing more to say."""


@dataclass(frozen=True)
class RubricReport:
    dimensions: list[Dimension]

    @property
    def total(self) -> int:
        return sum(d.score for d in self.dimensions)

    def to_dict(self) -> dict[str, Any]:
        """Rubric-only payload. Used as a sub-object inside the combined
        quality_report.json. Note: `passed` here means "rubric ≥ 60" only —
        not the combined gate decision (which sits at the top level)."""
        return {
            "total": self.total,
            "passed": self.total >= 60,
            "dimensions": [
                {
                    "name": d.name,
                    "max": d.max,
                    "score": d.score,
                    "detail": d.detail,
                    "findings": d.findings,
                }
                for d in self.dimensions
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Capability-interface names that form the "known" leaf set for BFS.
# ---------------------------------------------------------------------------
_CAPABILITY_INTERFACES: frozenset[str] = frozenset(
    {"PaymentsConnector", "MandateConnector"}
)


@dataclass(frozen=True)
class RegisteredClass:
    """Static-analysis result for a package's registered connector class.

    Attributes:
        name: The class name captured from the second positional arg of
            ``ConnectorFactory.register("<psp>", X)`` in ``__init__.py``.
        capability_bases: The subset of the transitive base-name closure that
            are known capability interfaces (``PaymentsConnector``,
            ``MandateConnector``).  Always a ``frozenset``; the tests coerce
            it with ``set()``.
    """

    name: str
    capability_bases: frozenset[str]


def _extract_register_class_name(init_text: str) -> str | None:
    """Return the second positional arg name from the first
    ``ConnectorFactory.register(...)`` call, or ``None`` if not found.

    Accepts either AST (preferred) or falls back to a simple regex so that
    non-parseable ``__init__.py`` files don't hard-crash the rubric.
    """
    # Try AST first — most reliable.
    try:
        tree = ast.parse(init_text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            # Match ConnectorFactory.register(...)
            func = call.func
            is_register = (
                isinstance(func, ast.Attribute)
                and func.attr == "register"
                and isinstance(func.value, ast.Name)
                and func.value.id == "ConnectorFactory"
            )
            if not is_register:
                continue
            # Second positional arg (index 1) is the class name.
            if len(call.args) >= 2:
                arg = call.args[1]
                if isinstance(arg, ast.Name):
                    return arg.id
    except SyntaxError:
        pass

    # Regex fallback: ConnectorFactory.register("<psp>", ClassName)
    m = re.search(
        r"""ConnectorFactory\.register\(\s*["'][^"']*["']\s*,\s*([A-Za-z_]\w*)""",
        init_text,
    )
    return m.group(1) if m else None


def _build_class_bases_map(pkg: Path) -> dict[str, list[str]]:
    """AST-parse every ``*.py`` under *pkg* and return a mapping
    ``{class_name: [direct_base_name, ...]}``.

    Base names are extracted as:
    - ``ast.Name.id`` for simple names (``Connector``, ``_DemoBase``).
    - ``ast.Attribute.attr`` for dotted names (``lens.connector.Connector``
      → ``"Connector"``).

    Classes with the same name in different modules are merged (last-wins for
    the base list, but for BFS purposes any occurrence is sufficient — we only
    care about reachability, not which file defined a class).
    """
    result: dict[str, list[str]] = {}
    for py_file in pkg.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases: list[str] = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            result[node.name] = bases
    return result


def _transitive_bases(start: str, bases_map: dict[str, list[str]]) -> set[str]:
    """BFS from *start* through *bases_map* and return the full set of
    reachable names (excluding *start* itself).

    Names not in *bases_map* are leaves — they are still included in the
    result so that ``PaymentsConnector`` / ``MandateConnector`` (which are
    external to the fixture package and thus won't appear as ``ClassDef``
    nodes) are present when the BFS reaches them.
    """
    visited: set[str] = set()
    queue: deque[str] = deque(bases_map.get(start, []))
    while queue:
        name = queue.popleft()
        if name in visited:
            continue
        visited.add(name)
        for parent in bases_map.get(name, []):
            if parent not in visited:
                queue.append(parent)
    return visited


def resolve_registered_class(pkg: Path) -> RegisteredClass:
    """Resolve the class registered via ``ConnectorFactory.register`` in
    *pkg*'s ``__init__.py`` and compute its transitive capability bases.

    Algorithm (Design §OQ-A):
    1. Parse ``__init__.py``; capture second positional arg of
       ``ConnectorFactory.register("<psp>", X)`` → class name *X*.
    2. AST-parse every ``*.py`` under *pkg*; build ``{class_name: [bases]}``.
    3. BFS from *X* through the map to collect the transitive base-name set.
    4. ``capability_bases = transitive_names ∩ _CAPABILITY_INTERFACES``.

    Raises:
        ValueError: if ``__init__.py`` is missing or has no register call.
    """
    init_py = pkg / "__init__.py"
    if not init_py.is_file():
        raise ValueError(f"{pkg}: missing __init__.py")

    init_text = init_py.read_text(encoding="utf-8", errors="replace")
    class_name = _extract_register_class_name(init_text)
    if class_name is None:
        raise ValueError(
            f"{pkg}: no ConnectorFactory.register call with a class-name arg found"
        )

    bases_map = _build_class_bases_map(pkg)
    transitive = _transitive_bases(class_name, bases_map)
    cap_bases = frozenset(transitive & _CAPABILITY_INTERFACES)

    return RegisteredClass(name=class_name, capability_bases=cap_bases)


def composition_findings(pkg: Path) -> list[str]:
    """Return a list of human-readable findings about the registered class's
    capability composition, or an empty list if everything is fine.

    Rules checked here (T12 scope only):
    - The package must have a resolvable register call.
    - The registered class must transitively inherit at least one of
      ``PaymentsConnector`` or ``MandateConnector``.

    Returns:
        An empty list when compliant; a non-empty list of finding strings
        (each containing "capability interface") otherwise.
    """
    try:
        result = resolve_registered_class(pkg)
    except ValueError as exc:
        return [f"cannot resolve registered class: {exc}; must implement a capability interface"]
    if not result.capability_bases:
        return [
            f"registered class {result.name!r} does not implement a capability interface "
            f"(must inherit PaymentsConnector and/or MandateConnector, not bare Connector)"
        ]
    return []


def _score_marker(output_dir: Path) -> Dimension:
    py_files = list(output_dir.rglob("*.py"))
    if not py_files:
        return Dimension("marker_conformance", 5, 0, "no .py files emitted")
    missing = [str(p.relative_to(output_dir)) for p in py_files if not has_marker(p)]
    if missing:
        return Dimension("marker_conformance", 5, 0, f"missing/malformed marker: {missing[:3]}")
    return Dimension("marker_conformance", 5, 5, "all files carry the §4 marker")


def _parse_mypy_findings(stdout: str) -> list[str]:
    """Split mypy --strict output into one entry per error/note line.

    Drops blank lines and the `Found N errors ...` / `Success: ...` summary.
    Keeps `: error:` and `: note:` lines (notes give context — e.g. the file
    where a type was defined — that's useful when fixing the error).
    """
    out: list[str] = []
    for line in stdout.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith(("Found ", "Success:")):
            continue
        if ": error:" in line or ": note:" in line:
            out.append(line)
    return out


def _summarize_mypy(findings: list[str]) -> str:
    if not findings:
        return "mypy failed (no parseable errors)"
    errors = sum(1 for f in findings if ": error:" in f)
    notes = sum(1 for f in findings if ": note:" in f)
    return f"mypy failed: {errors} error(s)" + (f", {notes} note(s)" if notes else "")


# ---------------------------------------------------------------------------
# Deprecated typing aliases — Part 3
# ---------------------------------------------------------------------------

# Aliases that are deprecated in 3.9+ (use built-in generics instead).
_DEPRECATED_TYPING_ALIASES: frozenset[str] = frozenset(
    {
        "Dict",
        "FrozenSet",
        "List",
        "Optional",
        "Set",
        "Tuple",
        "Type",
    }
)

# Patterns for: `from typing import ..., Optional, ...`  or  `typing.Optional`
_DEPRECATED_IMPORT_RE = re.compile(
    r"\bfrom\s+typing\s+import\b|"
    r"\bimport\s+typing\b|"
    r"\btyping\."
)


def modern_typing_findings(pkg: Path) -> list[str]:
    """Return a list of findings for deprecated ``typing`` aliases used across
    all ``.py`` files under *pkg*.

    Flags: ``Dict``, ``List``, ``Optional``, ``Set``, ``Tuple``, ``FrozenSet``,
    ``Type`` (the aliases superseded by built-in generics in Python 3.9+).
    Allows: ``Callable``, ``Mapping``, ``Any``, ``Literal``, ``Iterable``,
    ``Sequence``, and any other name from ``typing`` not in the deprecated set.

    Strategy: AST-parse each file; walk ``ImportFrom`` nodes where module is
    ``"typing"`` and collect alias names that are in ``_DEPRECATED_TYPING_ALIASES``;
    also walk ``Attribute`` nodes for ``typing.<DeprecatedAlias>``.
    Falls back gracefully on ``SyntaxError`` (skips the file).

    Returns:
        A list of human-readable strings such as
        ``"core/models.py: uses deprecated typing alias Optional"``.
    """
    findings: list[str] = []
    for py_file in pkg.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue
        rel = py_file.relative_to(pkg)
        file_aliases: list[str] = []
        for node in ast.walk(tree):
            # from typing import Optional, Dict, ...
            if isinstance(node, ast.ImportFrom) and node.module in ("typing", "typing_extensions"):
                for alias in node.names:
                    if alias.name in _DEPRECATED_TYPING_ALIASES:
                        file_aliases.append(alias.name)
            # typing.Optional  / typing.Dict  (attribute access)
            elif isinstance(node, ast.Attribute):
                value = node.value
                if isinstance(value, ast.Name) and value.id == "typing" and node.attr in _DEPRECATED_TYPING_ALIASES:
                    file_aliases.append(node.attr)
        for found_alias in sorted(set(file_aliases)):
            findings.append(f"{rel}: uses deprecated typing alias {found_alias}")
    return findings


def _score_type_correctness(mypy_report: MypyReport, pkg: Path | None = None) -> Dimension:
    """Score type correctness.

    First checks mypy --strict; if that passes, also runs ``modern_typing_findings``
    on *pkg* (when provided) to catch deprecated aliases that mypy doesn't flag
    in strict mode.  Either failure docks the score to 0.
    """
    if not mypy_report.passed:
        findings = _parse_mypy_findings(mypy_report.stdout)
        return Dimension(
            name="type_correctness",
            max=20,
            score=0,
            detail=_summarize_mypy(findings),
            findings=findings,
        )

    if pkg is not None:
        alias_findings = modern_typing_findings(pkg)
        if alias_findings:
            return Dimension(
                name="type_correctness",
                max=20,
                score=0,
                detail=f"deprecated typing aliases: {alias_findings[0]}",
                findings=alias_findings,
            )

    return Dimension("type_correctness", 20, 20, "mypy --strict clean")


def _parse_pytest_findings(stdout: str) -> list[str]:
    """Pull the most useful lines out of a failed pytest run.

    Captures: collection errors, individual test failures (`FAILED`/`ERROR`
    lines), and the short test summary block at the end. Drops banner output,
    rerun hints, etc.
    """
    out: list[str] = []
    in_short_summary = False
    for line in stdout.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("=") and "short test summary" in line:
            in_short_summary = True
            continue
        if line.startswith("=") and in_short_summary:
            in_short_summary = False
            continue
        if in_short_summary:
            out.append(line)
            continue
        # Outside the short-summary block, only capture FAILED / ERROR markers
        # (one per failing case) + collection errors.
        if line.startswith(("FAILED ", "ERROR ")):
            out.append(line)
        elif "Interrupted: " in line and "error" in line.lower():
            out.append(line)
    return out


def _score_coverage(pytest_report: PytestReport) -> Dimension:
    pct = pytest_report.coverage_pct or 0.0
    if pct >= 80.0:
        return Dimension("test_coverage", 25, 25, f"coverage {pct:.1f}% ≥ 80%")
    score = int(round((pct / 80.0) * 25))
    findings = _parse_pytest_findings(pytest_report.stdout)
    return Dimension(
        name="test_coverage",
        max=25,
        score=score,
        detail=f"coverage {pct:.1f}% < 80%",
        findings=findings,
    )


# ---------------------------------------------------------------------------
# Domain-modular public-surface scorer (v2) — T13/T14
# ---------------------------------------------------------------------------

# Always-required files for a 0.2.0 domain-modular package.
_V2_CORE_FILES = [
    "core/base.py",
    "core/auth.py",
    "core/status.py",
    "core/models.py",
    "connector.py",
    "webhooks.py",
    "__init__.py",
]

# Per-domain required files (relative to pkg/<domain>/).
_V2_DOMAIN_FILES = {
    "orders": ["connector.py", "status_map.py", "webhooks.py"],
    "subscriptions": ["connector.py", "status_map.py", "webhooks.py"],
}

# Per-domain required methods (must be resolvable across the registered class's MRO).
_V2_DOMAIN_METHODS: dict[str, list[str]] = {
    "orders": [
        "create_order",
        "sync_payment",
        "refund",
        "sync_refund",
        "supported_methods",
        "supports_idempotency_key",
    ],
    "subscriptions": [
        # lifecycle
        "create_subscription",
        "sync_subscription",
        "cancel_subscription",
        "pause_subscription",
        "resume_subscription",
        "create_plan",
        "change_plan",
        # introspection
        "supported_mandate_rails",
        "supports_pause",
        "supported_intervals",
        "max_mandate_amount",
    ],
}

# The known set of domains (in iteration order — future-proof against new ones).
_KNOWN_DOMAINS = ("orders", "subscriptions")

# Per-domain required enum references in status_map.py (T14 §4).
_V2_STATUS_MAP_ENUMS: dict[str, list[str]] = {
    "orders": ["PaymentAttemptStatus", "PaymentFailureCode"],
    "subscriptions": ["MandateStatus", "WebhookEventType"],
}


def _build_class_methods_map(pkg: Path) -> dict[str, set[str]]:
    """AST-parse every ``*.py`` under *pkg* and return a mapping
    ``{class_name: {method_name, ...}}``.

    When the same class name appears in multiple files the method sets are
    *merged* (union) — this handles the case where a mixin adds methods that
    are defined in a different file from the class's primary definition.
    Properties and regular/async methods are all collected (the rubric
    checks names, not call-style).
    """
    result: dict[str, set[str]] = {}
    for py_file in pkg.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods: set[str] = set()
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(member.name)
            if node.name not in result:
                result[node.name] = methods
            else:
                result[node.name] |= methods
    return result


def _all_methods_in_mro(start: str, bases_map: dict[str, list[str]], methods_map: dict[str, set[str]]) -> set[str]:
    """Collect all method names reachable from *start* via BFS through
    *bases_map*, merging method sets from *methods_map* at each class.

    External names (e.g. ``PaymentsConnector``) that are not in *methods_map*
    are silently skipped — they live outside the package.
    """
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    all_methods: set[str] = set()
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        if name in methods_map:
            all_methods |= methods_map[name]
        for base in bases_map.get(name, []):
            if base not in seen:
                queue.append(base)
    return all_methods


def _check_init_registration(init_text: str) -> list[str]:
    """Return issues with the __init__.py registration block.

    Checks:
    - ``ConnectorFactory.register(...)`` is present.
    - ``ConnectorFactory.register_webhook(...)`` is present.
    """
    issues: list[str] = []
    if "ConnectorFactory.register(" not in init_text:
        issues.append("__init__.py: does not call ConnectorFactory.register")
    if "ConnectorFactory.register_webhook(" not in init_text:
        issues.append("__init__.py: does not call ConnectorFactory.register_webhook")
    return issues


def _check_webhooks_exports(pkg: Path) -> list[str]:
    """Return issues with the root webhooks.py export."""
    webhooks_py = pkg / "webhooks.py"
    if not webhooks_py.is_file():
        return ["webhooks.py: missing"]
    text = webhooks_py.read_text(encoding="utf-8", errors="replace")
    if "build_webhook_handlers" not in text:
        return ["webhooks.py: does not define/export build_webhook_handlers"]
    return []


def _check_domain_status_maps(pkg: Path, present_domains: list[str]) -> list[str]:
    """For each present domain, verify its ``status_map.py`` references the
    required enums (T14 §4).

    - ``orders/status_map.py`` must reference ``PaymentAttemptStatus`` AND
      ``PaymentFailureCode``.
    - ``subscriptions/status_map.py`` must reference ``MandateStatus`` AND
      ``WebhookEventType``.

    Missing references dock + appear in detail.
    """
    issues: list[str] = []
    for domain in present_domains:
        required_enums = _V2_STATUS_MAP_ENUMS.get(domain, [])
        if not required_enums:
            continue
        status_map_py = pkg / domain / "status_map.py"
        if not status_map_py.is_file():
            # Already caught by domain-file presence check; don't double-report.
            continue
        text = status_map_py.read_text(encoding="utf-8", errors="replace")
        for enum_name in required_enums:
            if enum_name not in text:
                issues.append(
                    f"{domain}/status_map.py: does not reference {enum_name}"
                )
    return issues


def _score_public_surface_v2(pkg: Path) -> Dimension:
    """Score the public surface of a domain-modular 0.2.0 connector package.

    Checks (in order):
    1.  Registered class composes ≥1 capability interface (reuses composition_findings).
    2.  Required core files always present.
    3.  Per-present-domain required files.
    4.  Per-present-domain required methods (resolved transitively via MRO BFS).
    5.  __init__.py calls both register + register_webhook.
    6.  root webhooks.py exports build_webhook_handlers.
    7.  Per-present-domain status_map.py references required enums.

    Absent domains are NOT penalized (Cross-Cutting C1).
    Score starts at max 20; each issue docks a penalty; clamped ≥ 0.
    """
    issues: list[str] = []

    # 1. Capability-interface composition.
    comp = composition_findings(pkg)
    issues.extend(comp)

    # 2. Core required files.
    for rel in _V2_CORE_FILES:
        if not (pkg / rel).is_file():
            issues.append(f"missing {rel}")

    # 3 & 4. Per-domain checks (only for domains whose directory is present).
    present_domains = [d for d in _KNOWN_DOMAINS if (pkg / d).is_dir()]

    # Pre-build method resolution data once (shared across domains).
    bases_map = _build_class_bases_map(pkg)
    methods_map = _build_class_methods_map(pkg)

    # Resolve the registered class name for MRO traversal.
    registered_name: str | None = None
    init_py = pkg / "__init__.py"
    if init_py.is_file():
        registered_name = _extract_register_class_name(
            init_py.read_text(encoding="utf-8", errors="replace")
        )

    mro_methods: set[str] = set()
    if registered_name:
        mro_methods = _all_methods_in_mro(registered_name, bases_map, methods_map)

    for domain in present_domains:
        domain_dir = pkg / domain
        # 3. Domain file presence.
        for rel in _V2_DOMAIN_FILES.get(domain, []):
            if not (domain_dir / rel).is_file():
                issues.append(f"missing {domain}/{rel}")
        # 4. Domain method presence (resolved across MRO).
        for method in _V2_DOMAIN_METHODS.get(domain, []):
            if method not in mro_methods:
                issues.append(f"{domain}: missing method {method}")

    # 5. Registration checks.
    if init_py.is_file():
        init_text = init_py.read_text(encoding="utf-8", errors="replace")
        issues.extend(_check_init_registration(init_text))

    # 6. Root webhooks.py exports build_webhook_handlers.
    issues.extend(_check_webhooks_exports(pkg))

    # 7. Per-domain status_map enum references.
    issues.extend(_check_domain_status_maps(pkg, present_domains))

    if not issues:
        return Dimension(
            "public_surface",
            20,
            20,
            "all required files + methods + registration present",
        )

    # Build detail from the first few issues; mention every missing method name
    # explicitly so tests can grep for them.
    penalty = min(20, 4 * len(issues))
    detail = "; ".join(issues[:5])
    return Dimension("public_surface", 20, max(0, 20 - penalty), detail)


# ---------------------------------------------------------------------------
# Error-handling scorer v2 — T14 Part 1
# ---------------------------------------------------------------------------


def _score_error_handling_v2(pkg: Path) -> Dimension:
    """Score error-handling quality for a domain-modular 0.2.0 connector.

    The webhook signature failure now lives in the SHARED webhook layer.
    Checks:
    - root ``webhooks.py`` exports ``build_webhook_handlers`` AND references
      ``WEBHOOK_SIGNATURE_FAILED`` (via the ``verify`` callable) — OR that
      ``_classify`` / ``WebhookFamily`` + ``WebhookHandlers`` wiring is present.
    - ``ConnectorError`` is referenced somewhere in the package.
    - httpx errors are wrapped (any per-domain connector.py using httpx must
      call ``raise_for_status`` or catch ``HTTPStatusError``).

    Max 20.
    """
    issues: list[str] = []

    # Check 1: root webhooks.py has build_webhook_handlers + signature check.
    webhooks_py = pkg / "webhooks.py"
    if not webhooks_py.is_file():
        issues.append("webhooks.py: missing")
    else:
        text = webhooks_py.read_text(encoding="utf-8", errors="replace")
        if "build_webhook_handlers" not in text:
            issues.append("webhooks.py: does not define/export build_webhook_handlers")
        # Signature failure check: either WEBHOOK_SIGNATURE_FAILED directly, or
        # WebhookFamily/_classify/WebhookHandlers wiring (domain-modular pattern).
        has_sig_check = (
            "WEBHOOK_SIGNATURE_FAILED" in text
            or ("WebhookFamily" in text and "_classify" in text)
            or ("WebhookHandlers" in text and "verify" in text)
        )
        if not has_sig_check:
            issues.append(
                "webhooks.py: no WEBHOOK_SIGNATURE_FAILED reference "
                "(or WebhookFamily/_classify/WebhookHandlers.verify wiring)"
            )

    # Check 2: ConnectorError referenced somewhere in the package.
    connector_error_found = False
    for py_file in pkg.rglob("*.py"):
        try:
            if "ConnectorError" in py_file.read_text(encoding="utf-8", errors="replace"):
                connector_error_found = True
                break
        except OSError:
            continue
    if not connector_error_found:
        issues.append("package: no ConnectorError references found")

    # Check 3: httpx errors wrapped in any domain connector.py that uses httpx.
    for domain in _KNOWN_DOMAINS:
        domain_connector = pkg / domain / "connector.py"
        if not domain_connector.is_file():
            continue
        try:
            text = domain_connector.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if (
            "httpx" in text
            and "raise_for_status" not in text
            and "HTTPStatusError" not in text
        ):
            issues.append(f"{domain}/connector.py: httpx errors not wrapped")

    # Also check root connector.py for httpx usage.
    root_connector = pkg / "connector.py"
    if root_connector.is_file():
        try:
            text = root_connector.read_text(encoding="utf-8", errors="replace")
            if (
                "httpx" in text
                and "raise_for_status" not in text
                and "HTTPStatusError" not in text
            ):
                issues.append("connector.py: httpx errors not wrapped")
        except OSError:
            pass

    if not issues:
        return Dimension("error_handling", 20, 20, "ConnectorError + signature check present")
    penalty = min(20, 7 * len(issues))
    return Dimension("error_handling", 20, max(0, 20 - penalty), "; ".join(issues))


# ---------------------------------------------------------------------------
# PII discipline scorer — T14 Part 2 (relocated to core/auth.py)
# ---------------------------------------------------------------------------


def _score_pii_discipline(output_dir: Path) -> Dimension:
    """Score PII discipline for a domain-modular 0.2.0 connector.

    Checks:
    - ``core/auth.py`` contains ``Maskable`` (relocated from root ``auth.py``).
    - No secret-named values in log calls across the package.
    """
    issues: list[str] = []
    core_auth_py = output_dir / "core" / "auth.py"
    if core_auth_py.is_file():
        text = core_auth_py.read_text(encoding="utf-8", errors="replace")
        if "Maskable" not in text:
            issues.append("core/auth.py: credentials not typed Maskable")
    else:
        issues.append("core/auth.py missing")
    forbidden_re = re.compile(r"(structlog|logger|logging)\.\w+\([^)]*\bsecret\b", re.IGNORECASE)
    for p in output_dir.rglob("*.py"):
        try:
            if forbidden_re.search(p.read_text(encoding="utf-8", errors="replace")):
                issues.append(f"{p.relative_to(output_dir)}: secret in log call")
        except OSError:
            continue
    if not issues:
        return Dimension("pii_discipline", 10, 10, "Maskable used; no obvious PII in logs")
    penalty = min(10, 4 * len(issues))
    return Dimension("pii_discipline", 10, max(0, 10 - penalty), "; ".join(issues))


def score_rubric(
    *,
    ctx: GenerationContext,
    output_dir: Path,
    mypy_report: MypyReport,
    pytest_report: PytestReport,
) -> RubricReport:
    return RubricReport(
        dimensions=[
            _score_marker(output_dir),
            _score_type_correctness(mypy_report, output_dir),
            _score_coverage(pytest_report),
            _score_public_surface_v2(output_dir),
            _score_error_handling_v2(output_dir),
            _score_pii_discipline(output_dir),
        ]
    )
