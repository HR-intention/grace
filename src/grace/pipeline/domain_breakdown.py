"""Per-domain quality-gate breakdown helpers.

Pure functions: no I/O, no Lens imports. Given mypy stdout, pytest stdout, and
the coverage.json dict (already loaded by the caller), build a mapping from
domain bucket → {mypy_errors, tests_failed, covered_lines, num_statements,
coverage_pct}.

Bucketing rules (precedence order):
  - path contains `/<psp>/core/`          → "core"
  - path contains `/<psp>/orders/`        → "orders"
  - path contains `/<psp>/subscriptions/` → "subscriptions"
  - package-root compose file (`/<psp>/connector.py`, `/<psp>/webhooks.py`,
    `/<psp>/__init__.py`)                 → "root"
  - anything else under the package       → "other"

Test bucketing (same precedence):
  1. If the test path contains a `/orders/` or `/subscriptions/` segment, use it.
  2. Otherwise apply a filename heuristic:
       create_order / sync_payment / refund / sync_refund → "orders"
       subscription / mandate                             → "subscriptions"
       webhook_router / webhook                           → "root"  (cross-domain)
  NOTE: the heuristic is "exact once tests are domain-foldered (a later rulebook
  fix)". When the test layout migrates to `tests/.../cashfree/orders/test_x.py`
  the path-segment rule (step 1) will fire automatically.
"""

from __future__ import annotations

import re
from collections import defaultdict

# Regex to detect a PSP connector path segment; we look for the repeating
# directory markers rather than requiring a specific PSP name.
_ROOT_FILES = frozenset({"connector.py", "webhooks.py", "__init__.py"})

# Filename stems / substrings that map to an orders domain.
_ORDERS_KEYWORDS = ("create_order", "sync_payment", "refund", "sync_refund")
# Filename stems / substrings that map to a subscriptions domain.
_SUBSCRIPTIONS_KEYWORDS = ("subscription", "mandate", "plan")
# Filename stems / substrings that map to the root (cross-domain webhook router).
_ROOT_KEYWORDS = ("webhook_router", "webhook")


def domain_of_file(path: str) -> str:
    """Return the domain bucket for a source file path.

    Precedence: core > orders > subscriptions > root > other.
    Matching is done on forward-slash-normalised path segments.
    """
    # Normalise Windows separators just in case.
    p = path.replace("\\", "/")

    if "/core/" in p:
        return "core"
    if "/orders/" in p:
        return "orders"
    if "/subscriptions/" in p:
        return "subscriptions"

    # Package-root compose files: the *filename* (last segment) is one of the
    # known root files AND there is no sub-domain directory in the path.
    filename = p.rsplit("/", 1)[-1]
    if filename in _ROOT_FILES:
        return "root"

    return "other"


def domain_of_test(test_id: str) -> str:
    """Return the domain bucket for a pytest test identifier.

    *test_id* is the full pytest node id, e.g.
      ``tests/integration/connectors/cashfree/orders/test_sync.py::test_x``
      ``tests/integration/connectors/cashfree/test_refund.py::test_x``

    Step 1 — path-segment precedence (exact once tests are domain-foldered):
      If the path portion contains ``/orders/`` or ``/subscriptions/``, use it.

    Step 2 — filename heuristic (flat layout):
      Strip the ``::…`` node suffix, take the filename stem, and match
      against keyword lists.
    """
    # Extract the file path part (before the first `::`)
    file_part = test_id.split("::")[0].replace("\\", "/")

    # Step 1: path segment takes precedence.
    if "/subscriptions/" in file_part:
        return "subscriptions"
    if "/orders/" in file_part:
        return "orders"

    # Step 2: filename heuristic.
    filename = file_part.rsplit("/", 1)[-1]
    # Remove leading "test_" prefix and extension for cleaner matching.
    stem = re.sub(r"^test_", "", filename)
    stem = re.sub(r"\.py$", "", stem)

    for kw in _ORDERS_KEYWORDS:
        if kw in stem:
            return "orders"
    # webhook_router must be checked before generic "webhook" to avoid
    # over-broad matching, but we list it first in _ROOT_KEYWORDS already.
    for kw in _ROOT_KEYWORDS:
        if kw in stem:
            return "root"
    for kw in _SUBSCRIPTIONS_KEYWORDS:
        if kw in stem:
            return "subscriptions"

    return "other"


def build_domain_breakdown(
    *,
    mypy_stdout: str,
    pytest_stdout: str,
    coverage: dict[str, object] | None,
) -> dict[str, dict[str, int | float]]:
    """Aggregate per-domain quality metrics from raw tool outputs.

    Returns a dict mapping domain bucket → metric dict.  Only domains that
    have at least one data point are included.  Each present domain has the
    shape::

        {
            "mypy_errors":    int,
            "tests_failed":   int,
            "covered_lines":  int,
            "num_statements": int,
            "coverage_pct":   float,
        }

    All values default to 0 / 0.0 for a domain that has data from *some*
    sources but not others (e.g. mypy errors but no coverage info).
    """
    # Accumulator: domain → mutable metric dict.
    acc: dict[str, dict[str, int | float]] = defaultdict(
        lambda: {
            "mypy_errors": 0,
            "tests_failed": 0,
            "covered_lines": 0,
            "num_statements": 0,
            "coverage_pct": 0.0,
        }
    )

    # --- mypy errors ---
    for line in mypy_stdout.splitlines():
        if ": error:" not in line:
            continue
        # mypy lines: `<path>:<lineno>: error: <msg> [<code>]`
        file_path = line.split(":")[0]
        domain = domain_of_file(file_path)
        acc[domain]["mypy_errors"] = int(acc[domain]["mypy_errors"]) + 1

    # --- pytest failures ---
    for line in pytest_stdout.splitlines():
        line = line.rstrip()
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            # Strip the leading keyword; the rest is the test node id.
            test_id = line.split(" ", 1)[1].strip()
            domain = domain_of_test(test_id)
            acc[domain]["tests_failed"] = int(acc[domain]["tests_failed"]) + 1

    # --- coverage ---
    if coverage is not None:
        files_data = coverage.get("files")
        if isinstance(files_data, dict):
            for file_path, file_info in files_data.items():
                if not isinstance(file_info, dict):
                    continue
                summary = file_info.get("summary", {})
                if not isinstance(summary, dict):
                    continue
                covered = summary.get("covered_lines", 0)
                statements = summary.get("num_statements", 0)
                if not isinstance(covered, (int, float)) or not isinstance(
                    statements, (int, float)
                ):
                    continue
                domain = domain_of_file(file_path)
                acc[domain]["covered_lines"] = int(acc[domain]["covered_lines"]) + int(covered)
                acc[domain]["num_statements"] = int(acc[domain]["num_statements"]) + int(
                    statements
                )

    # Compute coverage_pct from aggregated covered/total for each domain.
    result: dict[str, dict[str, int | float]] = {}
    for domain, metrics in acc.items():
        total = int(metrics["num_statements"])
        covered = int(metrics["covered_lines"])
        pct: float = (covered / total * 100.0) if total > 0 else 0.0
        result[domain] = {
            "mypy_errors": int(metrics["mypy_errors"]),
            "tests_failed": int(metrics["tests_failed"]),
            "covered_lines": covered,
            "num_statements": total,
            "coverage_pct": pct,
        }

    return result
