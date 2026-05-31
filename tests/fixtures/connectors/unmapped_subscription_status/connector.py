from __future__ import annotations

from .orders.connector import DemoOrders
from .subscriptions.connector import DemoSubscriptions


class DemoConnector(DemoOrders, DemoSubscriptions):
    pass
