from __future__ import annotations

from grace.pipeline.types import GenerationContext


PROMPT_TEMPLATE = """\
You are generating a Python PSP connector for the Orbit Lens.

Target package layout (you will create these files in the current working directory):

  __init__.py
  connector.py
  auth.py
  models.py
  status_map.py
  tests/test_create_order.py
  tests/test_sync_payment.py
  tests/test_refund.py
  tests/test_sync_refund.py
  tests/test_webhook.py

Hard constraints:
  1. Every .py file MUST start with the generated-file marker exactly as defined in the rulebook.
  2. The class implements the locked Connector ABC. Do not rename properties or methods.
  3. Use only the domain types from lens.domain_types and lens.enums.
  4. mypy --strict must be clean. No `Any`.
  5. Tests use httpx.MockTransport. Do not hit live PSPs.
  6. PSP-specific status terms must be mapped through status_map.py into PaymentAttemptStatus + PaymentFailureCode.

Context — read these files in order:
{rulebook_block}

PSP source — the target PSP's documentation:
{source_block}

Target module: {target_module}
Generator version: grace {grace_version}
Source version: {source_version}
Lens version constraint: {lens_version_constraint}

Generate the package. Do not ask follow-up questions. Write the files and exit.
"""


def build_prompt(ctx: GenerationContext) -> str:
    rulebook_block = "\n".join(f"  - {p}" for p in ctx.rulebook_paths)
    if ctx.psp_docs.source_kind == "url":
        source_block = (
            f"  - URL: {ctx.psp_docs.source_uri}\n"
            f"  - Content fetched at generation time "
            f"(use the Read tool on the cached file: see CWD)."
        )
    else:
        source_block = "\n".join(f"  - {p}" for p in ctx.psp_docs.local_paths)
    return PROMPT_TEMPLATE.format(
        rulebook_block=rulebook_block,
        source_block=source_block,
        target_module=ctx.target_module,
        grace_version=ctx.grace_version,
        source_version=ctx.source_version,
        lens_version_constraint=ctx.lens_version_constraint,
    )
