from __future__ import annotations

requires_lens = "^0.2"

from .connector import PartialConnector
from .webhooks import build_webhook_handlers
from lens.factory import ConnectorFactory

ConnectorFactory.register("partial", PartialConnector)
ConnectorFactory.register_webhook("partial", build_webhook_handlers)
