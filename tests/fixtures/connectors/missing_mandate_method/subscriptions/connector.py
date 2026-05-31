from __future__ import annotations

from lens.mandate_connector import MandateConnector

from ..core.base import _PartialBase


class PartialSubscriptions(_PartialBase, MandateConnector):
    @property
    def supported_mandate_rails(self) -> set[str]:
        return {"UPI_AUTOPAY"}

    @property
    def supports_pause(self) -> bool:
        return True

    @property
    def supported_intervals(self) -> set[str]:
        return {"MONTHLY"}

    @property
    def max_mandate_amount(self) -> int:
        return 50000

    async def create_subscription(self, request: object) -> object:
        ...

    async def sync_subscription(self, request: object) -> object:
        ...

    # cancel_subscription intentionally OMITTED to trigger a dock

    async def pause_subscription(self, request: object) -> object:
        ...

    async def resume_subscription(self, request: object) -> object:
        ...
