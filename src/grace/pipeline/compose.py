"""Grace-owned compose-surface generator.

Writes three deterministic files at the package root of a generated PSP connector:
  - connector.py  — merged registered class (MRO: domain mixins in order)
  - webhooks.py   — build_webhook_handlers + _classify
  - __init__.py   — ConnectorFactory registration + requires_lens

This module does NOT stamp the §4 marker — ``orchestrate.run_pipeline`` calls
``ensure_marker`` on every emitted .py after the compose step (T11).
"""

from __future__ import annotations

from pathlib import Path

from grace.errors import GraceError, GraceErrorReason

# Ordered list of supported domains. The ordering here determines the MRO so
# orders always precedes subscriptions in the generated base-class tuple.
_DOMAIN_ORDER: list[str] = ["orders", "subscriptions"]


def _psp_title(psp_name: str) -> str:
    """'cashfree' → 'Cashfree'."""
    return psp_name[:1].upper() + psp_name[1:]


def _domain_class(psp_title: str, domain: str) -> str:
    """('Cashfree', 'orders') → 'CashfreeOrders'."""
    return f"{psp_title}{domain[:1].upper() + domain[1:]}"


# ---------------------------------------------------------------------------
# Template builders — pure string functions for testability
# ---------------------------------------------------------------------------

def _render_connector(psp_title: str, present: list[str]) -> str:
    domain_classes = [_domain_class(psp_title, d) for d in present]
    imports = "\n".join(
        f"from .{domain}.connector import {cls}"
        for domain, cls in zip(present, domain_classes)
    )
    bases = ", ".join(domain_classes)
    merged = f"{psp_title}Connector"
    return (
        f'"""Compose surface: {merged} merges present domain mixins."""\n'
        f"from __future__ import annotations\n"
        f"\n"
        f"{imports}\n"
        f"\n"
        f"\n"
        f"class {merged}({bases}):\n"
        f"    pass\n"
    )


def _render_webhooks(psp_title: str, present: list[str]) -> str:  # noqa: ARG001
    has_orders = "orders" in present
    has_subscriptions = "subscriptions" in present

    lines: list[str] = [
        '"""Webhook compose surface: verify once, classify, dispatch by family."""',
        "from __future__ import annotations",
        "",
        "import json",
        "",
        "from lens.webhook import WebhookFamily, WebhookHandlers",
        "from lens.factory import ConnectorConfig",
        "",
        "from .core.auth import verify_signature",
    ]

    if has_orders:
        lines.append("from .orders.webhooks import _parse_payment_webhook")
    if has_subscriptions:
        lines.append("from .subscriptions.webhooks import _parse_mandate_webhook")

    lines += [
        "",
        "",
        "def _classify(raw: bytes) -> WebhookFamily:",
        '    """Route to PAYMENT or MANDATE by inspecting the event type field."""',
        "    try:",
        '        envelope = json.loads(raw)',
        '        event_type: str = envelope.get("type", "") or envelope.get("event_type", "")',
        "    except (json.JSONDecodeError, AttributeError):",
        "        return WebhookFamily.PAYMENT",
        '    if event_type.startswith("SUBSCRIPTION_") or event_type.startswith("MANDATE_"):',
        "        return WebhookFamily.MANDATE",
        "    return WebhookFamily.PAYMENT",
        "",
        "",
        "def build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers:",
        "    return WebhookHandlers(",
        "        verify=lambda raw, headers: verify_signature(config, raw, headers),",
        "        classify=_classify,",
    ]

    if has_orders:
        lines.append("        parse_payment=_parse_payment_webhook,")
    if has_subscriptions:
        lines.append("        parse_mandate=_parse_mandate_webhook,")

    lines.append("    )")
    lines.append("")

    return "\n".join(lines)


def _render_init(psp_name: str, psp_title: str, lens_version: str) -> str:
    merged = f"{psp_title}Connector"
    return (
        f'"""Package registration for {psp_name}."""\n'
        f"from __future__ import annotations\n"
        f"\n"
        f'requires_lens = "{lens_version}"\n'
        f"\n"
        f"from .connector import {merged}\n"
        f"from .webhooks import build_webhook_handlers\n"
        f"from lens.factory import ConnectorFactory\n"
        f"\n"
        f'ConnectorFactory.register("{psp_name}", {merged})\n'
        f'ConnectorFactory.register_webhook("{psp_name}", build_webhook_handlers)\n'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_compose_surface(
    pkg: Path,
    *,
    psp_name: str,
    lens_version: str,
) -> None:
    """Write connector.py, webhooks.py, and __init__.py under *pkg*.

    Args:
        pkg:           Root directory of the generated PSP package
                       (e.g. ``<output_dir>/cashfree/``).
        psp_name:      Lower-case PSP identifier (e.g. ``"cashfree"``).
        lens_version:  PEP-440 version constraint to embed in __init__
                       (e.g. ``"^0.2"``).

    Raises:
        GraceError: When no supported domain directories are present under *pkg*.
    """
    present = [d for d in _DOMAIN_ORDER if (pkg / d).is_dir()]
    if not present:
        raise GraceError(
            reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
            detail=f"no domain directories found under {pkg}; expected at least one of {_DOMAIN_ORDER}",
        )

    psp_title = _psp_title(psp_name)

    (pkg / "connector.py").write_text(_render_connector(psp_title, present))
    (pkg / "webhooks.py").write_text(_render_webhooks(psp_title, present))
    (pkg / "__init__.py").write_text(_render_init(psp_name, psp_title, lens_version))
