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


REQUIRED_FILES = ("__init__.py", "connector.py", "auth.py", "models.py", "status_map.py")
LOCKED_FLOWS = ("create_order", "sync_payment", "refund", "sync_refund", "handle_webhook")


@dataclass(frozen=True)
class ConnectorSummary:
    """Static-analysis snapshot of one connector package."""

    psp_name: str                          # registry key, lowercase, from ConnectorFactory.register
    class_name: str                        # PascalCase class name from `class <Foo>(Connector):`
    pkg_dir: Path                          # absolute path to lens/connectors/<psp>/
    flows: list[str]                       # subset of LOCKED_FLOWS actually defined
    supported_methods: list[str]           # values from the `supported_methods` property
    base_url: str | None                   # literal string returned by `base_url`
    psp_status_terms: list[str]            # keys of STATUS_MAP in status_map.py
    requires_lens: str | None              # `requires_lens = "..."` from __init__.py
    self_registers: bool                   # whether __init__.py calls ConnectorFactory.register


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


def introspect_connector(pkg_dir: Path) -> ConnectorSummary:
    """Return a ConnectorSummary for the connector package at `pkg_dir`."""
    init_text = _read_safely(pkg_dir / "__init__.py")
    connector_text = _read_safely(pkg_dir / "connector.py")
    status_map_text = _read_safely(pkg_dir / "status_map.py")

    self_registers, registry_name, requires_lens = _init_facts(init_text)

    class_name = "Unknown"
    flows: list[str] = []
    supported_methods: list[str] = []
    base_url: str | None = None
    psp_name_from_class: str | None = None

    try:
        tree = ast.parse(connector_text)
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

    return ConnectorSummary(
        psp_name=psp_name,
        class_name=class_name,
        pkg_dir=pkg_dir,
        flows=flows,
        supported_methods=sorted(supported_methods),
        base_url=base_url,
        psp_status_terms=_status_map_keys(status_map_text),
        requires_lens=requires_lens,
        self_registers=self_registers,
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
        "  3. Call the four flows (async): create_order -> sync_payment ->",
        "     refund -> sync_refund. Use handle_webhook(raw_payload, headers)",
        "     for incoming PSP events; close() at shutdown.",
        "  4. Branch on returned status enums (OrderStatus, PaymentAttemptStatus,",
        "     RefundStatus) — never PSP-specific strings.",
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
