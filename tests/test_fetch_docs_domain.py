from grace.fetch_docs import bucket_for_url, filter_urls_by_domain

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
