from __future__ import annotations

from lens.common import WEBHOOK_SIGNATURE_FAILED, ConnectorError


def build_webhook_handlers(config: object) -> object:
    # verify raises ConnectorError(WEBHOOK_SIGNATURE_FAILED) on bad signatures
    ...
