from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

from grace.pipeline.gates import MypyReport, PytestReport
from grace.pipeline.marker import has_marker
from grace.pipeline.types import GenerationContext


@dataclass(frozen=True)
class Dimension:
    name: str
    max: int
    score: int
    detail: str


@dataclass(frozen=True)
class RubricReport:
    dimensions: list[Dimension]

    @property
    def total(self) -> int:
        return sum(d.score for d in self.dimensions)

    def to_json(self) -> str:
        return json.dumps(
            {
                "total": self.total,
                "passed": self.total >= 60,
                "dimensions": [
                    {"name": d.name, "max": d.max, "score": d.score, "detail": d.detail}
                    for d in self.dimensions
                ],
            },
            indent=2,
        )


# --- required public surface (per SUBPROJECT_GRACE_CODEGEN.md §3.2 + §5) ---
REQUIRED_FILES = ["__init__.py", "connector.py", "auth.py", "models.py", "status_map.py"]
REQUIRED_TEST_FILES = [
    "tests/test_create_order.py",
    "tests/test_sync_payment.py",
    "tests/test_refund.py",
    "tests/test_sync_refund.py",
    "tests/test_webhook.py",
]
REQUIRED_FLOW_METHODS = {
    "create_order",
    "sync_payment",
    "refund",
    "sync_refund",
    "handle_webhook",
    "close",
}
REQUIRED_PROPERTIES = {
    "name",
    "base_url",
    "supported_methods",
    "supports_idempotency_key",
}


def _score_marker(output_dir: Path) -> Dimension:
    py_files = list(output_dir.rglob("*.py"))
    if not py_files:
        return Dimension("marker_conformance", 5, 0, "no .py files emitted")
    missing = [str(p.relative_to(output_dir)) for p in py_files if not has_marker(p)]
    if missing:
        return Dimension("marker_conformance", 5, 0, f"missing/malformed marker: {missing[:3]}")
    return Dimension("marker_conformance", 5, 5, "all files carry the §4 marker")


def _score_type_correctness(mypy_report: MypyReport) -> Dimension:
    if mypy_report.passed:
        return Dimension("type_correctness", 20, 20, "mypy --strict clean")
    return Dimension(
        "type_correctness", 20, 0, f"mypy failed: {mypy_report.stdout.strip()[:200]}"
    )


def _score_coverage(pytest_report: PytestReport) -> Dimension:
    pct = pytest_report.coverage_pct or 0.0
    if pct >= 80.0:
        return Dimension("test_coverage", 25, 25, f"coverage {pct:.1f}% ≥ 80%")
    score = int(round((pct / 80.0) * 25))
    return Dimension("test_coverage", 25, score, f"coverage {pct:.1f}% < 80%")


def _score_public_surface(ctx: GenerationContext, output_dir: Path) -> Dimension:
    issues: list[str] = []
    for name in REQUIRED_FILES:
        if not (output_dir / name).is_file():
            issues.append(f"missing {name}")
    for name in REQUIRED_TEST_FILES:
        if not (output_dir / name).is_file():
            issues.append(f"missing {name}")

    connector_py = output_dir / "connector.py"
    if connector_py.is_file():
        tree: ast.Module | None
        try:
            tree = ast.parse(connector_py.read_text())
        except SyntaxError as e:
            issues.append(f"connector.py: parse error {e}")
            tree = None
        if tree is not None:
            class_node = next(
                (
                    n
                    for n in tree.body
                    if isinstance(n, ast.ClassDef) and n.name.lower() == ctx.psp_name.lower()
                ),
                None,
            )
            if class_node is None:
                issues.append(f"connector.py: no class named (case-insensitive) {ctx.psp_name}")
            else:
                method_names = {
                    n.name
                    for n in class_node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                missing = REQUIRED_FLOW_METHODS - method_names
                if missing:
                    issues.append(f"connector class missing methods: {sorted(missing)}")

                # Detect missing @property declarations. An abstract Connector
                # with these missing fails to instantiate at register-time,
                # so test_coverage collapses to 0 — surface it here instead
                # of waiting for pytest collection to blow up.
                property_names: set[str] = set()
                for member in class_node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in member.decorator_list:
                            # `@property` is an ast.Name.
                            if isinstance(dec, ast.Name) and dec.id == "property":
                                property_names.add(member.name)
                                break
                missing_props = REQUIRED_PROPERTIES - property_names
                if missing_props:
                    issues.append(
                        f"connector class missing @property declarations: "
                        f"{sorted(missing_props)}"
                    )

    init_py = output_dir / "__init__.py"
    if init_py.is_file():
        text = init_py.read_text()
        if "ConnectorFactory.register" not in text:
            issues.append("__init__.py: does not call ConnectorFactory.register")
        if "requires_lens" not in text:
            issues.append("__init__.py: missing requires_lens")

    status_map_py = output_dir / "status_map.py"
    if status_map_py.is_file():
        if "PaymentAttemptStatus" not in status_map_py.read_text():
            issues.append("status_map.py: does not reference PaymentAttemptStatus")

    if not issues:
        return Dimension(
            "public_surface",
            20,
            20,
            "all required files + methods + registration present",
        )
    penalty = min(20, 4 * len(issues))
    return Dimension("public_surface", 20, 20 - penalty, "; ".join(issues[:5]))


def _score_error_handling(output_dir: Path) -> Dimension:
    issues: list[str] = []
    connector_py = output_dir / "connector.py"
    if connector_py.is_file():
        text = connector_py.read_text()
        if "WEBHOOK_SIGNATURE_FAILED" not in text:
            issues.append(
                "connector.py: handle_webhook does not raise ConnectorError(WEBHOOK_SIGNATURE_FAILED)"
            )
        if "ConnectorError" not in text:
            issues.append("connector.py: no ConnectorError references")
        if (
            "httpx" in text
            and "raise_for_status" not in text
            and "HTTPStatusError" not in text
        ):
            issues.append("connector.py: httpx errors not wrapped")
    else:
        issues.append("connector.py missing")
    if not issues:
        return Dimension("error_handling", 20, 20, "ConnectorError + signature check present")
    penalty = min(20, 7 * len(issues))
    return Dimension("error_handling", 20, 20 - penalty, "; ".join(issues))


def _score_pii_discipline(output_dir: Path) -> Dimension:
    issues: list[str] = []
    auth_py = output_dir / "auth.py"
    if auth_py.is_file():
        text = auth_py.read_text()
        if "Maskable" not in text:
            issues.append("auth.py: credentials not typed Maskable")
    else:
        issues.append("auth.py missing")
    forbidden_re = re.compile(r"(structlog|logger|logging)\.\w+\([^)]*\bsecret\b", re.IGNORECASE)
    for p in output_dir.rglob("*.py"):
        if forbidden_re.search(p.read_text()):
            issues.append(f"{p.relative_to(output_dir)}: secret in log call")
    if not issues:
        return Dimension("pii_discipline", 10, 10, "Maskable used; no obvious PII in logs")
    penalty = min(10, 4 * len(issues))
    return Dimension("pii_discipline", 10, 10 - penalty, "; ".join(issues))


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
            _score_type_correctness(mypy_report),
            _score_coverage(pytest_report),
            _score_public_surface(ctx, output_dir),
            _score_error_handling(output_dir),
            _score_pii_discipline(output_dir),
        ]
    )
