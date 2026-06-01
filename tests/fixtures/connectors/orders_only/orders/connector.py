from __future__ import annotations

from lens.payments_connector import PaymentsConnector

from ..core.base import _PayOnlyBase


class PayOnlyOrders(_PayOnlyBase, PaymentsConnector):
    @property
    def supported_methods(self) -> set[str]:
        return {"CARD"}

    @property
    def supports_idempotency_key(self) -> bool:
        return True

    async def create_order(self, request: object) -> object:
        ...

    async def sync_payment(self, request: object) -> object:
        ...

    async def refund(self, request: object) -> object:
        ...

    async def sync_refund(self, request: object) -> object:
        ...
