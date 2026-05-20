from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.fetch_docs import (
    derive_filename,
    fetch_docs,
    filter_urls,
    parse_llms_txt,
)


SAMPLE_LLMS_TXT = """
# Cashfree Payments Developer Documentation - URL List

## Documentation & Reference
- https://www.cashfree.com/docs/api-reference/authentication.md
- https://www.cashfree.com/docs/api-reference/integration-troubleshooting/overview-ts.md

## Orders
- https://www.cashfree.com/docs/api-reference/payments/latest/orders/create.md
- https://www.cashfree.com/docs/api-reference/payments/latest/orders/get.md

## Subscriptions - Mandate
- https://www.cashfree.com/docs/api-reference/payments/latest/subscription/mandate/create.md

## Previous Versions - v2022-09-01 - Orders
- https://www.cashfree.com/docs/api-reference/payments/previous/v2022-09-01/orders/create-order.md

## Refunds
- https://www.cashfree.com/docs/api-reference/payments/latest/refunds/create.md
- https://www.cashfree.com/docs/api-reference/payments/latest/refunds/webhooks.md
"""


def test_parse_llms_txt_extracts_urls() -> None:
    urls = parse_llms_txt(SAMPLE_LLMS_TXT)
    assert "https://www.cashfree.com/docs/api-reference/authentication.md" in urls
    assert "https://www.cashfree.com/docs/api-reference/payments/latest/orders/create.md" in urls
    assert len(urls) == 8


def test_parse_llms_txt_dedups() -> None:
    body = SAMPLE_LLMS_TXT + "\n- https://www.cashfree.com/docs/api-reference/authentication.md\n"
    urls = parse_llms_txt(body)
    assert urls.count("https://www.cashfree.com/docs/api-reference/authentication.md") == 1


def test_filter_urls_default_globs_keeps_v1_pages() -> None:
    urls = parse_llms_txt(SAMPLE_LLMS_TXT)
    kept = filter_urls(urls)
    kept_paths = {u.split(".com")[-1] for u in kept}
    # Latest orders + refunds survive (note: the leading-globs wildcard `*orders/*`
    # only requires the path contain `/orders/` — the latest variant matches).
    assert "/docs/api-reference/payments/latest/orders/create.md" in kept_paths
    assert "/docs/api-reference/payments/latest/refunds/webhooks.md" in kept_paths
    # Subscriptions, ts (troubleshooting), previous versions are filtered out.
    assert all("/subscription/" not in p for p in kept_paths)
    assert all("/previous/" not in p for p in kept_paths)
    assert all("overview-ts" not in p for p in kept_paths)


def test_filter_urls_explicit_include() -> None:
    urls = parse_llms_txt(SAMPLE_LLMS_TXT)
    kept = filter_urls(urls, include=["*/refunds/*"], exclude=[])
    kept_paths = {u.split(".com")[-1] for u in kept}
    assert all("/refunds/" in p for p in kept_paths)
    # auth + orders excluded by the include filter.
    assert all("/orders/" not in p for p in kept_paths)


def test_filter_urls_raises_when_everything_filtered() -> None:
    urls = parse_llms_txt(SAMPLE_LLMS_TXT)
    kept = filter_urls(urls, include=["*/nonexistent/*"], exclude=[])
    assert kept == []


def test_derive_filename_numbered_and_flat() -> None:
    name = derive_filename(
        "https://www.cashfree.com/docs/api-reference/payments/latest/orders/create.md", 5
    )
    assert name.startswith("05_")
    assert name.endswith(".md")
    assert "/" not in name


def test_fetch_docs_writes_filtered_files(tmp_path: Path) -> None:
    llms_txt_url = "https://example.com/docs/llms.txt"

    served: dict[str, bytes] = {
        llms_txt_url: SAMPLE_LLMS_TXT.encode(),
        "https://www.cashfree.com/docs/api-reference/payments/latest/orders/create.md": b"# create",
        "https://www.cashfree.com/docs/api-reference/payments/latest/orders/get.md": b"# get",
        "https://www.cashfree.com/docs/api-reference/payments/latest/refunds/create.md": b"# rcreate",
        "https://www.cashfree.com/docs/api-reference/payments/latest/refunds/webhooks.md": b"# rwh",
        "https://www.cashfree.com/docs/api-reference/authentication.md": b"# auth",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = served.get(str(request.url))
        if body is None:
            return httpx.Response(404, request=request)
        return httpx.Response(200, content=body, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = tmp_path / "connector_docs" / "cashfree"
    result = fetch_docs(
        psp_name="cashfree",
        source=llms_txt_url,
        output_dir=out,
        client=client,
    )
    client.close()

    names = sorted(p.name for p in result.files_written)
    assert any("orders_create" in n for n in names)
    assert any("orders_get" in n for n in names)
    assert any("refunds_create" in n for n in names)
    assert any("refunds_webhooks" in n for n in names)
    assert any("authentication" in n for n in names)
    # 8 URLs in sample; default filter drops subscriptions + previous + ts → 5 kept.
    assert len(result.files_written) == 5
    assert result.skipped_count == 3
    # Each file has the served body.
    for p in result.files_written:
        body = p.read_text()
        assert body.startswith("#")


def test_fetch_docs_raises_on_empty_llms_txt(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"# nothing here", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(GraceError) as exc:
        fetch_docs(
            psp_name="x",
            source="https://example.com/empty.txt",
            output_dir=tmp_path / "x",
            client=client,
        )
    client.close()
    assert exc.value.reason is GraceErrorReason.SOURCE_FETCH_FAILED


def test_fetch_docs_raises_when_all_filtered_out(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=SAMPLE_LLMS_TXT.encode(), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(GraceError) as exc:
        fetch_docs(
            psp_name="x",
            source="https://example.com/llms.txt",
            output_dir=tmp_path / "x",
            include=["*/no-such-section/*"],
            exclude=[],
            client=client,
        )
    client.close()
    assert exc.value.reason is GraceErrorReason.SOURCE_FETCH_FAILED


def test_fetch_docs_reads_local_llms_txt(tmp_path: Path) -> None:
    llms_txt_path = tmp_path / "llms.txt"
    llms_txt_path.write_text(SAMPLE_LLMS_TXT)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"# stub", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = fetch_docs(
        psp_name="cashfree",
        source=str(llms_txt_path),
        output_dir=tmp_path / "out",
        client=client,
    )
    client.close()
    assert len(result.files_written) == 5
