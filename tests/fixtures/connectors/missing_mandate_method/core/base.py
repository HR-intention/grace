from __future__ import annotations

from lens.connector import Connector


class _PartialBase(Connector):
    def __init__(self, config: object) -> None:
        ...

    @property
    def name(self) -> str:
        return "partial"

    @property
    def base_url(self) -> str:
        return "https://api.partial.example.com"

    async def close(self) -> None:
        ...
