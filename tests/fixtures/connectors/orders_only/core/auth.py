from __future__ import annotations

from lens.common import Maskable


class PayOnlyCredentials:
    api_key: Maskable[str]
