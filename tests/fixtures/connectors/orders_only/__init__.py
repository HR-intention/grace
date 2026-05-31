from __future__ import annotations

requires_lens = "^0.2"

from .connector import PayOnlyConnector
from .webhooks import build_webhook_handlers
from lens.factory import ConnectorFactory

ConnectorFactory.register("payonly", PayOnlyConnector)
ConnectorFactory.register_webhook("payonly", build_webhook_handlers)
