from __future__ import annotations

from .orders.connector import PartialOrders
from .subscriptions.connector import PartialSubscriptions


class PartialConnector(PartialOrders, PartialSubscriptions):
    pass
