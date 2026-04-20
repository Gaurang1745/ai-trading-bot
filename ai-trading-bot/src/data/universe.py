"""
Universe filter (Layer 1).
Pure mechanical filtering — no trading logic.
Removes ASM/GSM, T2T, low-price, and illiquid stocks.
Runs daily at 8:30 AM.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class UniverseFilter:
    """
    Filters the full instrument list down to tradeable stocks.
    Output: ~350-450 eligible symbols.
    """

    def __init__(self, instrument_manager, config: dict):

        self.instrument_manager = instrument_manager
        self.config = config
        self._eligible_universe: list[str] = []
        self._asm_gsm_list: set[str] = set()
        self._t2t_list: set[str] = set()

        # Config params
        self.min_price = config.get("trading", {}).get("min_stock_price", 20)
        self.min_volume_cr = config.get("trading", {}).get("min_daily_volume_cr", 1.0)
        self.approved_etfs = config.get("etfs", {}).get("approved", [])

    def refresh(self) -> list[str]:
        """
        Run the full universe filter pipeline.
        Returns list of eligible symbols.
        """
        logger.info("Running universe filter...")

        # Step 1: Get all equity instruments
        all_eq = self.instrument_manager.get_valid_symbols()
        logger.info(f"Total equity symbols: {len(all_eq)}")

        # Step 2: Load ASM/GSM list
        self._load_asm_gsm_list()

        # Step 3: Load T2T list
        self._load_t2t_list()

        # Step 4: Filter
        eligible = []
        filtered_reasons = {"asm_gsm": 0, "t2t": 0, "low_price": 0, "low_volume": 0}

        for symbol in sorted(all_eq):
            # Skip ASM/GSM stocks
            if symbol in self._asm_gsm_list:
                filtered_reasons["asm_gsm"] += 1
                continue

            # Skip T2T stocks
            if symbol in self._t2t_list:
                filtered_reasons["t2t"] += 1
                continue

            eligible.append(symbol)

        # Add approved ETFs (they may not be in EQ list)
        for etf in self.approved_etfs:
            if etf not in eligible:
                eligible.append(etf)

        self._eligible_universe = eligible
        logger.info(
            f"Universe filter complete: {len(eligible)} eligible symbols. "
            f"Filtered out: {filtered_reasons}"
        )

        return eligible

    def filter_by_price_and_volume(self, quotes: dict) -> list[str]:
        """
        Second-pass filter using live price and volume data.
        Called after quotes are available.
        quotes: dict of "EXCHANGE:SYMBOL" -> quote data
        """
        filtered = []
        for symbol in self._eligible_universe:
            # Try NSE first, then BSE
            quote = quotes.get(f"NSE:{symbol}") or quotes.get(f"BSE:{symbol}")
            if not quote:
                continue

            ltp = quote.get("last_price", 0)
            if ltp < self.min_price:
                continue

            # Volume check is done during bulk data collection
            # as it requires historical data for 20-day average
            filtered.append(symbol)

        logger.info(f"Price-filtered universe: {len(filtered)} symbols")
        return filtered

    def _load_asm_gsm_list(self) -> None:
        """Load ASM/GSM restricted stocks list."""
        asm_path = "data/asm_gsm_list.csv"
        if os.path.exists(asm_path):
            try:
                df = pd.read_csv(asm_path)
                if "symbol" in df.columns:
                    self._asm_gsm_list = set(df["symbol"].str.strip().tolist())
                elif "Symbol" in df.columns:
                    self._asm_gsm_list = set(df["Symbol"].str.strip().tolist())
                logger.info(f"Loaded {len(self._asm_gsm_list)} ASM/GSM stocks")
            except Exception as e:
                logger.warning(f"Failed to load ASM/GSM list: {e}")
        else:
            logger.warning(
                f"ASM/GSM list not found at {asm_path}. "
                "No ASM/GSM filtering will be applied. "
                "Download from NSE website and save as CSV."
            )

    def _load_t2t_list(self) -> None:
        """Load Trade-to-Trade segment stocks."""
        t2t_path = "data/t2t_list.csv"
        if os.path.exists(t2t_path):
            try:
                df = pd.read_csv(t2t_path)
                col = "symbol" if "symbol" in df.columns else "Symbol"
                if col in df.columns:
                    self._t2t_list = set(df[col].str.strip().tolist())
                logger.info(f"Loaded {len(self._t2t_list)} T2T stocks")
            except Exception as e:
                logger.warning(f"Failed to load T2T list: {e}")
        else:
            logger.info("T2T list not found. No T2T filtering applied.")

    def get_eligible_universe(self) -> list[str]:
        """Return cached eligible universe."""
        return self._eligible_universe.copy()

    def is_eligible(self, symbol: str) -> bool:
        """Check if a symbol is in the eligible universe."""
        return symbol in self._eligible_universe

    def get_asm_gsm_list(self) -> set[str]:
        """Return current ASM/GSM list for guardrail use."""
        return self._asm_gsm_list.copy()
