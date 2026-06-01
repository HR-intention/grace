"""Build the Lens-side `docs-generated/` artifacts (mirrors upstream's pattern).

Given a Lens checkout that has one or more `lens/connectors/<psp>/` packages,
emit:
  - `docs-generated/llms.txt` — a connector navigation index modeled on
    juspay-prism's `docs-generated/llms.txt`. Downstream AI agents (Orbit-the-
    product, future Symplora apps) fetch this first to see what's available.
  - `docs-generated/connectors/<psp>.md` — per-connector reference page with
    flows, supported payment methods, and the canonical example invocation.

Grace introspects the connector's `connector.py` via `ast` to extract
`name`, `base_url`, `supported_methods`, the four flow methods, and any
status-map entries from `status_map.py`. We never `import` the connector
package (Grace stays Lens-free); everything is static AST analysis.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason
from grace.quality_rubric import (
    _all_methods_in_mro,
    _build_class_bases_map,
    _build_class_methods_map,
    _extract_register_class_name,
)


REQUIRED_FILES = ("__init__.py", "connector.py", "auth.py", "models.py")

# Capability-keyed locked flows: payment domain + mandate domain.
# handle_webhook is NOT included — it is handled by the webhook layer, not
# by the capability interface.
LOCKED_FLOWS = (
    # Payment (orders) flows
    "create_order",
    "sync_payment",
    "refund",
    "sync_refund",
    # Mandate (subscriptions) lifecycle flows
    "create_subscription",
    "sync_subscription",
    "cancel_subscription",
    "pause_subscription",
    "resume_subscription",
)


@dataclass(frozen=True)
class ConnectorSummary:
    """Static-analysis snapshot of one connector package."""

    psp_name: str                          # registry key, lowercase, from ConnectorFactory.register
    class_name: str                        # PascalCase class name resolved via register() call
    pkg_dir: Path                          # absolute path to lens/connectors/<psp>/
    flows: list[str]                       # subset of LOCKED_FLOWS actually defined across MRO
    supported_methods: list[str]           # values from the `supported_methods` property
    base_url: str | None                   # literal string returned by `base_url`
    psp_status_terms: list[str]            # keys of STATUS_MAP in per-domain status_map.py files
    requires_lens: str | None              # `requires_lens = "..."` from __init__.py
    self_registers: bool                   # whether __init__.py calls ConnectorFactory.register
    domains: list[str] = field(default_factory=list)  # present capability domains


@dataclass(frozen=True)
class DocsBuildResult:
    output_root: Path                      # the docs-generated/ dir
    connectors: list[ConnectorSummary]
    files_written: list[Path] = field(default_factory=list)


# --------------------------------------------------------------------------
# AST introspection
# --------------------------------------------------------------------------


def _read_safely(p: Path) -> str:
    try:
        return p.read_text()
    except OSError:
        return ""


def _connector_class(tree: ast.Module) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                # Match `class Foo(Connector):`
                if isinstance(base, ast.Name) and base.id == "Connector":
                    return node
                # Match `class Foo(lens.connector.Connector):`
                if isinstance(base, ast.Attribute) and base.attr == "Connector":
                    return node
    return None


def _literal_str_returned(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """If the function body is a single `return "<literal>"`, return that string."""
    for stmt in node.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
            v = stmt.value.value
            if isinstance(v, str):
                return v
    return None


def _set_literal_strings(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """If the function returns `{PaymentMethod.X, PaymentMethod.Y}`, return ['X', 'Y']."""
    for stmt in node.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, (ast.Set, ast.List, ast.Tuple)):
            values: list[str] = []
            for elt in stmt.value.elts:
                # PaymentMethod.CARD -> "CARD"
                if isinstance(elt, ast.Attribute):
                    values.append(elt.attr)
                # "CARD" -> "CARD"
                elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.append(elt.value)
            return values
    return []


def _flows_defined(cls: ast.ClassDef) -> list[str]:
    method_names = {
        n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return [f for f in LOCKED_FLOWS if f in method_names]


def _flows_from_mro(mro_methods: set[str]) -> list[str]:
    """Return the subset of LOCKED_FLOWS present in the full MRO method set."""
    return [f for f in LOCKED_FLOWS if f in mro_methods]


def _property_body(cls: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _init_facts(init_text: str) -> tuple[bool, str | None, str | None]:
    """Return (self_registers, registry_name_arg, requires_lens_value)."""
    registers = "ConnectorFactory.register" in init_text

    name_match = re.search(
        r"""ConnectorFactory\.register\(\s*["']([^"']+)["']""", init_text
    )
    registry_name = name_match.group(1) if name_match else None

    rl_match = re.search(
        r"""requires_lens\s*=\s*["']([^"']+)["']""", init_text
    )
    requires_lens = rl_match.group(1) if rl_match else None

    return (registers, registry_name, requires_lens)


def _status_map_keys(status_map_text: str) -> list[str]:
    """Extract dict keys from STATUS_MAP / _PAYMENT_STATUS_MAP / similar."""
    try:
        tree = ast.parse(status_map_text)
    except SyntaxError:
        return []
    keys: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for key_expr in node.value.keys:
                if isinstance(key_expr, ast.Constant) and isinstance(key_expr.value, str):
                    keys.append(key_expr.value)
    # De-dupe, preserve order.
    seen: set[str] = set()
    deduped: list[str] = []
    for value in keys:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


_KNOWN_DOMAINS = ("orders", "subscriptions")


def _collect_domain_status_terms(pkg_dir: Path) -> list[str]:
    """Collect status-map keys from per-domain status_map.py files.

    Reads ``<pkg>/<domain>/status_map.py`` for each present domain (orders,
    subscriptions), falling back to the flat ``status_map.py`` at the
    package root for legacy connectors.  Results are de-duplicated across
    all sources while preserving first-seen order.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _merge(text: str) -> None:
        for term in _status_map_keys(text):
            if term not in seen:
                seen.add(term)
                result.append(term)

    # Per-domain files (domain-modular layout).
    found_domain_map = False
    for domain in _KNOWN_DOMAINS:
        domain_sm = pkg_dir / domain / "status_map.py"
        if domain_sm.is_file():
            found_domain_map = True
            _merge(_read_safely(domain_sm))

    # Legacy fallback: flat status_map.py at the package root.
    if not found_domain_map:
        _merge(_read_safely(pkg_dir / "status_map.py"))

    return result


def introspect_connector(pkg_dir: Path) -> ConnectorSummary:
    """Return a ConnectorSummary for the connector package at ``pkg_dir``.

    Resolution strategy (domain-modular layout):

    1. Read ``__init__.py``; extract the class name from the second arg of
       ``ConnectorFactory.register("<psp>", ClassName)`` via
       ``_extract_register_class_name`` (from ``grace.quality_rubric``).
    2. AST-parse every ``*.py`` under ``pkg_dir`` to build the full
       ``{class_name: [bases]}`` and ``{class_name: {methods}}`` maps.
    3. BFS over the MRO to collect all method names reachable from the
       registered class.
    4. The ``flows`` list is the intersection of those methods with
       ``LOCKED_FLOWS`` (payment + mandate lifecycle; no ``handle_webhook``).

    Fallback for legacy flat-layout connectors: if no register call exists
    the old ``class Foo(Connector)`` detection is used so existing tests
    continue to pass.
    """
    init_text = _read_safely(pkg_dir / "__init__.py")
    connector_text = _read_safely(pkg_dir / "connector.py")

    self_registers, registry_name, requires_lens = _init_facts(init_text)

    class_name: str = "Unknown"
    flows: list[str] = []
    supported_methods: list[str] = []
    base_url: str | None = None
    psp_name_from_class: str | None = None

    # --- Step 1: Resolve registered class name via __init__.py. ---
    registered_name = _extract_register_class_name(init_text)

    if registered_name is not None:
        # --- Steps 2–4: MRO-based resolution. ---
        class_name = registered_name
        bases_map = _build_class_bases_map(pkg_dir)
        methods_map = _build_class_methods_map(pkg_dir)
        mro_methods = _all_methods_in_mro(registered_name, bases_map, methods_map)
        flows = _flows_from_mro(mro_methods)

        # Extract supported_methods and base_url from the nearest class in the
        # MRO that defines the property (search all AST-parsed class bodies).
        for cls_name, method_set in methods_map.items():
            if "supported_methods" in method_set and not supported_methods:
                # Find the class def to extract the literal set.
                for py_file in pkg_dir.rglob("*.py"):
                    try:
                        t = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
                    except (OSError, SyntaxError):
                        continue
                    for node in ast.walk(t):
                        if isinstance(node, ast.ClassDef) and node.name == cls_name:
                            sm_node = _property_body(node, "supported_methods")
                            if sm_node is not None:
                                cands = _set_literal_strings(sm_node)
                                if cands:
                                    supported_methods = cands
                            break

        # base_url: walk all classes in the MRO to find a literal return.
        for py_file in pkg_dir.rglob("*.py"):
            if base_url is not None:
                break
            try:
                t = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(t):
                if isinstance(node, ast.ClassDef):
                    burl_node = _property_body(node, "base_url")
                    if burl_node is not None:
                        candidate = _literal_str_returned(burl_node)
                        if candidate is not None:
                            base_url = candidate
                            break

        # psp_name from `name` property.
        for py_file in pkg_dir.rglob("*.py"):
            if psp_name_from_class is not None:
                break
            try:
                t = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(t):
                if isinstance(node, ast.ClassDef):
                    name_node = _property_body(node, "name")
                    if name_node is not None:
                        candidate = _literal_str_returned(name_node)
                        if candidate is not None:
                            psp_name_from_class = candidate
                            break

    else:
        # Fallback: legacy flat-layout connector (class Foo(Connector): ...).
        try:
            tree: ast.Module | None = ast.parse(connector_text)
        except SyntaxError:
            tree = None

        if tree is not None:
            cls = _connector_class(tree)
            if cls is not None:
                class_name = cls.name
                flows = _flows_defined(cls)
                sm_node = _property_body(cls, "supported_methods")
                if sm_node is not None:
                    supported_methods = _set_literal_strings(sm_node)
                burl_node = _property_body(cls, "base_url")
                if burl_node is not None:
                    base_url = _literal_str_returned(burl_node)
                name_node = _property_body(cls, "name")
                if name_node is not None:
                    psp_name_from_class = _literal_str_returned(name_node)

    psp_name = registry_name or psp_name_from_class or pkg_dir.name

    # Determine present domains.
    domains = [d for d in _KNOWN_DOMAINS if (pkg_dir / d).is_dir()]

    return ConnectorSummary(
        psp_name=psp_name,
        class_name=class_name,
        pkg_dir=pkg_dir,
        flows=flows,
        supported_methods=sorted(supported_methods),
        base_url=base_url,
        psp_status_terms=_collect_domain_status_terms(pkg_dir),
        requires_lens=requires_lens,
        self_registers=self_registers,
        domains=domains,
    )


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def discover_connectors(lens_root: Path, connectors_subpath: str = "lens/connectors") -> list[Path]:
    """Find every connector package under `<lens_root>/<connectors_subpath>/`.

    `connectors_subpath` is consumer-configurable via `paths.output_dir` —
    e.g., src-layout Lens checkouts set it to `src/lens/connectors`. Default
    matches the original flat layout for backward compat.
    """
    connectors_dir = lens_root / connectors_subpath
    if not connectors_dir.is_dir():
        return []
    return sorted(
        p
        for p in connectors_dir.iterdir()
        if p.is_dir()
        and not p.name.startswith(("_", "."))
        and (p / "connector.py").is_file()
    )


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------


def render_llms_txt(connectors: list[ConnectorSummary]) -> str:
    """Render the navigation index in the upstream juspay-prism shape."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        "# Lens — LLM Navigation Index",
        f"# Connectors: {len(connectors)}",
        f"# Generated: {now}",
        "#",
        "# This file lists every PSP connector available in this Lens checkout.",
        "# Downstream AI agents integrating against Lens should fetch this first,",
        "# then fetch the specific connector doc under docs-generated/connectors/.",
        "",
        "overview:",
        f"  total_connectors: {len(connectors)}",
        "  docs_root: docs-generated/connectors/",
        "  package_root: lens/connectors/",
        "",
        "integration_pattern:",
        "  1. Build a ConnectorConfig with the PSP's credentials (api_key,",
        "     secret_key, webhook_secret — all Maskable[str]).",
        "  2. Use ConnectorFactory.create(config) to obtain the Connector.",
        "  3. Payment flows (async): create_order -> sync_payment -> refund ->",
        "     sync_refund. Mandate flows: create_subscription -> sync_subscription",
        "     -> cancel_subscription (pause/resume where supported).",
        "  4. Webhook events are dispatched via ConnectorFactory.register_webhook;",
        "     call close() at shutdown.",
        "  5. Branch on returned status enums (OrderStatus, PaymentAttemptStatus,",
        "     RefundStatus, MandateStatus) — never PSP-specific strings.",
        "",
    ]
    for c in connectors:
        lines.append("---")
        lines.append("")
        lines.append(f"## {c.class_name}")
        lines.append(f"connector_id: {c.psp_name}")
        lines.append(f"doc: docs-generated/connectors/{c.psp_name}.md")
        lines.append(f"package: lens/connectors/{c.psp_name}/")
        lines.append(f"class: lens.connectors.{c.psp_name}.connector.{c.class_name}")
        lines.append(f"requires_lens: {c.requires_lens or 'unknown'}")
        lines.append(f"self_registers: {'yes' if c.self_registers else 'NO (broken)'}")
        if c.base_url:
            lines.append(f"base_url: {c.base_url}")
        if c.supported_methods:
            lines.append(f"payment_methods: {', '.join(c.supported_methods)}")
        if c.flows:
            lines.append(f"flows: {', '.join(c.flows)}")
        if c.psp_status_terms:
            lines.append(f"psp_status_terms: {', '.join(c.psp_status_terms)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_connector_md(c: ConnectorSummary) -> str:
    """Render a per-connector reference page."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = [
        f"# {c.class_name}",
        "",
        "> Autogenerated by `grace docs`. Do not edit by hand. "
        f"Last refreshed: {now}.",
        "",
        "## Quick facts",
        "",
        f"- Registry key: `\"{c.psp_name}\"`",
        f"- Python class: `lens.connectors.{c.psp_name}.connector.{c.class_name}`",
        f"- Requires Lens: `{c.requires_lens or 'unknown'}`",
        f"- Self-registers on import: `{c.self_registers}`",
    ]
    if c.base_url:
        lines.append(f"- Base URL: `{c.base_url}`")
    lines.append("")
    if c.supported_methods:
        lines.append("## Supported payment methods")
        lines.append("")
        for m in c.supported_methods:
            lines.append(f"- `{m}`")
        lines.append("")
    if c.flows:
        lines.append("## Flows implemented")
        lines.append("")
        for f in c.flows:
            lines.append(f"- `{f}`")
        lines.append("")
    if c.psp_status_terms:
        lines.append("## PSP-specific status terms")
        lines.append("")
        lines.append("Mapped to `(PaymentAttemptStatus, PaymentFailureCode | None)` "
                     "by `status_map.py`:")
        lines.append("")
        for term in c.psp_status_terms:
            lines.append(f"- `{term}`")
        lines.append("")
    lines.append("## Example")
    lines.append("")
    lines.append("```python")
    lines.append("from lens.factory import ConnectorFactory, ConnectorConfig")
    lines.append("from lens.common import Maskable")
    lines.append("")
    lines.append(f"# self-registration on import: `import lens.connectors.{c.psp_name}`")
    lines.append("config = ConnectorConfig(")
    lines.append(f'    name="{c.psp_name}",')
    lines.append('    api_key=Maskable("..."),')
    lines.append('    secret_key=Maskable("..."),')
    lines.append('    webhook_secret=Maskable("..."),')
    lines.append(")")
    lines.append("connector = ConnectorFactory.create(config)")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def build_docs(*, lens_root: Path, connectors_subpath: str = "lens/connectors") -> DocsBuildResult:
    """Discover every connector under lens_root and emit docs-generated/.

    `connectors_subpath` mirrors `paths.output_dir` from the consumer's
    grace config (e.g., `src/lens/connectors` for src-layout Lens). The
    docs catalog is written to `<lens_root>/docs-generated/` regardless.
    """
    pkgs = discover_connectors(lens_root, connectors_subpath)
    if not pkgs:
        raise GraceError(
            reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
            detail=(
                f"no connector packages under {lens_root}/{connectors_subpath}/ — "
                f"run `grace generate <psp>` first or check `paths.output_dir` "
                f"in `grace config show`."
            ),
        )
    connectors = [introspect_connector(p) for p in pkgs]

    out_root = lens_root / "docs-generated"
    connectors_dir = out_root / "connectors"
    connectors_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    llms_txt_path = out_root / "llms.txt"
    llms_txt_path.write_text(render_llms_txt(connectors))
    written.append(llms_txt_path)

    for c in connectors:
        md_path = connectors_dir / f"{c.psp_name}.md"
        md_path.write_text(render_connector_md(c))
        written.append(md_path)

    return DocsBuildResult(
        output_root=out_root,
        connectors=connectors,
        files_written=written,
    )
