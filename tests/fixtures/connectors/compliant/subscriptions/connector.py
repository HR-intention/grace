from __future__ import annotations

from lens.mandate_connector import MandateConnector

from ..core.base import _DemoBase


class DemoSubscriptions(_DemoBase, MandateConnector):
    def supported_mandate_rails(self) -> set[str]:
        return {"UPI_AUTOPAY"}

    def supports_pause(self) -> bool:
        return True

    def supported_intervals(self) -> set[str]:
        return {"MONTHLY", "WEEKLY"}

    def max_mandate_amount(self) -> int:
        return 100000

    async def create_subscription(self, request: object) -> object:
        ...

    async def sync_subscription(self, request: object) -> object:
        ...

    async def cancel_subscription(self, request: object) -> object:
        ...

    async def pause_subscription(self, request: object) -> object:
        ...

    async def resume_subscription(self, request: object) -> object:
        ...
