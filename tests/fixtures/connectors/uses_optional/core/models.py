from __future__ import annotations

from typing import Optional, Dict


class DemoConfig:
    api_key: Optional[str] = None
    extra: Dict[str, str] = {}
