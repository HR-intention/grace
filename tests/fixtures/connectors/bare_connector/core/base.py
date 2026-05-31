from __future__ import annotations

from lens.connector import Connector


class _BareBase(Connector):
    def __init__(self, config: object) -> None:
        ...

    @property
    def name(self) -> str:
        return "bare"

    @property
    def base_url(self) -> str:
        return "https://api.bare.example.com"

    async def close(self) -> None:
        ...
