from __future__ import annotations

from lens.connector import Connector


class _PayOnlyBase(Connector):
    def __init__(self, config: object) -> None:
        ...

    @property
    def name(self) -> str:
        return "payonly"

    @property
    def base_url(self) -> str:
        return "https://api.payonly.example.com"

    async def close(self) -> None:
        ...
