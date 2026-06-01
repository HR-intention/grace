from __future__ import annotations

from lens.common import Maskable


class DemoCredentials:
    api_key: Maskable[str]
    webhook_secret: Maskable[str]
