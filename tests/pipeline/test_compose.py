from grace.pipeline.compose import write_compose_surface


def _mk_domain(pkg, domain, cls):
    d = pkg / domain; d.mkdir(parents=True)
    (d / "connector.py").write_text(f"class {cls}:\n    pass\n")
    (d / "__init__.py").write_text("")


def test_compose_both_domains(tmp_path) -> None:
    pkg = tmp_path / "cashfree"
    _mk_domain(pkg, "orders", "CashfreeOrders")
    _mk_domain(pkg, "subscriptions", "CashfreeSubscriptions")
    write_compose_surface(pkg, psp_name="cashfree")
    conn = (pkg / "connector.py").read_text()
    assert "class CashfreeConnector(CashfreeOrders, CashfreeSubscriptions)" in conn
    init = (pkg / "__init__.py").read_text()
    assert 'ConnectorFactory.register("cashfree", CashfreeConnector)' in init
    assert 'ConnectorFactory.register_webhook("cashfree", build_webhook_handlers)' in init
    assert "requires_lens" not in init      # version gate removed in constitution v0.6
    hooks = (pkg / "webhooks.py").read_text()
    assert "parse_mandate=" in hooks and "parse_payment=" in hooks


def test_compose_orders_only_has_no_mandate_parser(tmp_path) -> None:
    pkg = tmp_path / "razorpay"
    _mk_domain(pkg, "orders", "RazorpayOrders")
    write_compose_surface(pkg, psp_name="razorpay")
    assert "class RazorpayConnector(RazorpayOrders)" in (pkg / "connector.py").read_text()
    hooks = (pkg / "webhooks.py").read_text()
    assert "parse_payment=" in hooks
    assert "parse_mandate=" not in hooks      # absent domain omitted
