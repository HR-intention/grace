from __future__ import annotations

requires_lens = "^0.2"

from .connector import BareConnector
from .webhooks import build_webhook_handlers
from lens.factory import ConnectorFactory

ConnectorFactory.register("bare", BareConnector)
ConnectorFactory.register_webhook("bare", build_webhook_handlers)
