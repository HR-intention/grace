from __future__ import annotations

from lens.connector import Connector


class _DemoBase(Connector):
    def __init__(self, config: object) -> None:
        ...

    @property
    def name(self) -> str:
        return "demo"

    @property
    def base_url(self) -> str:
        return "https://api.demo.example.com"

    async def close(self) -> None:
        ...
