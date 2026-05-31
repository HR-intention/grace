import pytest

import httpx

from grace.errors import GraceError
from grace.fetch_docs import bucket_for_url, derive_filename, fetch_docs, filter_urls_by_domain

URLS = [
    "https://x/docs/api-reference/payments/latest/orders/create.md",
    "https://x/docs/api-reference/payments/latest/refunds/create.md",
    "https://x/docs/api-reference/subscription/mandate/create.md",
    "https://x/docs/api-reference/subscription/plans/create.md",
    "https://x/docs/api-reference/authentication.md",
    "https://x/docs/payments/online/webhooks/signature-verification.md",
    "https://x/docs/api-reference/subscriptionsv1/overview.md",  # legacy — must drop
]


def test_orders_domain_keeps_orders_and_shared_only() -> None:
    kept = filter_urls_by_domain(URLS, domain="orders")
    assert any("orders/create" in u for u in kept)
    assert any("authentication" in u for u in kept)          # shared
    assert not any("subscription/" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)


def test_subscriptions_domain_keeps_subs_and_shared_not_orders() -> None:
    kept = filter_urls_by_domain(URLS, domain="subscriptions")
    assert any("subscription/mandate/create" in u for u in kept)
    assert any("signature-verification" in u for u in kept)  # shared
    assert not any("/orders/" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)


def test_all_domain_is_union_minus_legacy() -> None:
    kept = filter_urls_by_domain(URLS, domain="all")
    assert any("orders/create" in u for u in kept)
    assert any("subscription/mandate/create" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)


def test_bucket_for_url() -> None:
    assert bucket_for_url("https://x/docs/api-reference/payments/latest/orders/create.md") == "orders"
    assert bucket_for_url("https://x/docs/api-reference/subscription/mandate/create.md") == "subscriptions"
    assert bucket_for_url("https://x/docs/api-reference/authentication.md") == "_shared"


def test_bucket_subscriptions_beats_orders_for_overlap_url() -> None:
    # A subscription payment/webhook page matches both *subscription/* and
    # *payments*webhook*; subscriptions must win (more specific bucket).
    url = "https://x/docs/api-reference/subscription/payments/webhook.md"
    assert bucket_for_url(url) == "subscriptions"


def test_filter_urls_by_domain_raises_on_unknown_domain() -> None:
    with pytest.raises(GraceError):
        filter_urls_by_domain(URLS, domain="bogus")


def test_fetch_writes_into_domain_subfolders(tmp_path) -> None:
    # URLs are written to match the real domain globs used by filter_urls_by_domain.
    # *api*orders*  -> orders bucket
    # *subscription/mandate*  -> subscriptions bucket
    # *api*authentication*  -> _shared bucket
    pages = {
        "https://x/api-reference/payments/latest/orders/create.md": b"# orders create",
        "https://x/api-reference/subscription/mandate/create.md": b"# mandate create",
        "https://x/api-reference/authentication.md": b"# auth",
    }
    llms = "\n".join(pages) + "\n"

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("llms.txt"):
            return httpx.Response(200, text=llms)
        return httpx.Response(200, content=pages[str(req.url)])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = tmp_path / "cashfree"
    fetch_docs(
        psp_name="cashfree",
        source="https://x/llms.txt",
        output_dir=out,
        domain="all",
        client=client,
    )
    assert (out / "_shared").is_dir()
    # Each page should land in the correct bucket directory.
    assert list((out / "orders").glob("*.md")), "no files in orders bucket"
    assert list((out / "subscriptions").glob("*.md")), "no files in subscriptions bucket"
    assert list((out / "_shared").glob("*.md")), "no files in _shared bucket"
    # Verify the orders page filename contains the URL path segments.
    orders_files = list((out / "orders").glob("*.md"))
    assert any("orders" in f.name for f in orders_files), (
        f"expected orders-path file in orders bucket, got: {[f.name for f in orders_files]}"
    )
    subs_files = list((out / "subscriptions").glob("*.md"))
    assert any("mandate" in f.name for f in subs_files), (
        f"expected mandate file in subscriptions bucket, got: {[f.name for f in subs_files]}"
    )
