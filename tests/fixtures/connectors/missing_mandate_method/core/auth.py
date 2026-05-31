from __future__ import annotations

from lens.common import Maskable


class PartialCredentials:
    api_key: Maskable[str]
