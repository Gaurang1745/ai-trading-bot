"""
SL & Target Health Check.
Paper mode: delegates OHLC-based monitoring to PaperBroker.
"""

import logging

logger = logging.getLogger(__name__)


class SLHealthCheck:
    """
    Runs every 5 minutes during market hours.
    Delegates to PaperBroker for OHLC candle-based SL/target monitoring.
    """

    def __init__(self, db, notifier=None, config: dict = None,
                 market_data=None, paper_broker=None):
        self.db = db
        self.notifier = notifier
        self.config = config or {}
        self.market_data = market_data
        self.paper_broker = paper_broker

    def check(self):
        """Run the health check. Called every 5 minutes."""
        self.paper_broker.check_holding_sl_orders()
        self.paper_broker.check_position_sl_targets()
