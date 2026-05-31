from __future__ import annotations

requires_lens = "^0.2"

from .connector import DemoConnector
from .webhooks import build_webhook_handlers
from lens.factory import ConnectorFactory

ConnectorFactory.register("demo", DemoConnector)
# register_webhook call intentionally OMITTED to trigger a dock
