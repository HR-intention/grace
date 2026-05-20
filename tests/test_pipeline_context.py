from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.context import assemble_context, default_rulebook_paths, resolve_source


REPO_ROOT = Path(__file__).parent.parent


def test_default_rulebook_paths_returns_python_rulebook() -> None:
    paths = default_rulebook_paths(repo_root=REPO_ROOT)
    rels = {p.relative_to(REPO_ROOT).as_posix() for p in paths}
    assert "rulesbook/codegen/python/README.md" in rels
    assert "rulesbook/codegen/python/connector_abc.md" in rels
    assert "rulesbook/codegen/python/file_layout.md" in rels
    assert "rulesbook/codegen/python/marker.md" in rels


def test_resolve_source_local_file(tmp_path: Path) -> None:
    f = tmp_path / "openapi.yaml"
    f.write_text("openapi: 3.0.0")
    docs = resolve_source(str(f))
    assert docs.source_kind == "local_file"
    assert docs.local_paths == [f.resolve()]


def test_resolve_source_local_dir(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("x: 1")
    (tmp_path / "b.md").write_text("hello")
    docs = resolve_source(str(tmp_path))
    assert docs.source_kind == "local_dir"
    assert len(docs.local_paths) == 2


def test_resolve_source_url_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, **kwargs: object) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, text="openapi: 3.0.0", request=req)

    monkeypatch.setattr(httpx, "get", mock_get)
    docs = resolve_source("https://example.com/openapi.yaml")
    assert docs.source_kind == "url"
    assert docs.content_bytes == b"openapi: 3.0.0"


def test_resolve_source_url_404_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, **kwargs: object) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(404, text="not found", request=req)

    monkeypatch.setattr(httpx, "get", mock_get)
    with pytest.raises(GraceError) as exc:
        resolve_source("https://example.com/missing")
    assert exc.value.reason is GraceErrorReason.SOURCE_FETCH_FAILED


def test_assemble_context_end_to_end(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    ctx = assemble_context(
        psp_name="cashfree",
        source=str(spec),
        output_dir=tmp_path / "out",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
        repo_root=REPO_ROOT,
    )
    assert ctx.psp_name == "cashfree"
    assert ctx.target_module == "lens.connectors.cashfree"
    assert (tmp_path / "out").is_dir()
    assert any("python/connector_abc.md" in p.as_posix() for p in ctx.rulebook_paths)
