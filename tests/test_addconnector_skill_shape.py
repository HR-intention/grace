"""Structural assertions that the add-connector skill describes
the domain-modular lens-0.2.0 connector shape.

These tests exist to catch drift between the codegen rulebook (which drives
what Grace actually generates) and the human-facing skill doc (which tells
the operator how to drive Grace).  They are intentionally coarse — they
verify the presence of key phrases, not prose quality.
"""
from __future__ import annotations

from pathlib import Path

# Resolve relative to the repo root (parent of the tests/ directory) so these
# tests work regardless of the process cwd set by the conftest isolation fixture.
_REPO_ROOT = Path(__file__).parent.parent

SK = _REPO_ROOT / "src/grace/skills_templates/add-connector"
SH = _REPO_ROOT / "src/grace/skills_templates/_shared/references/flow-patterns"


def test_skill_describes_domain_modular_shape() -> None:
    skill = (SK / "SKILL.md").read_text()
    # The new CLI takes a --domain flag
    assert "--domain" in skill
    # Webhook registration is via register_webhook, not a connector method
    assert "register_webhook" in skill
    # The Phase-5 review checklist must reflect the composed class, not bare Connector
    assert "Connector(" in skill or "<Psp>Connector" in skill


def test_skill_webhook_pattern_is_shared_router() -> None:
    # The skill's webhook flow-pattern must not instruct a connector-method handle_webhook
    wh = SH / "handle_webhook.md"
    if wh.exists():
        t = wh.read_text()
        assert "build_webhook_handlers" in t  # rewritten to the shared router
