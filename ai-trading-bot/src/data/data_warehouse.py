"""
Data Warehouse (Layer 2).
Bulk data storage for the entire tradeable universe.
Pre-computes indicators, levels, patterns — ready for instant retrieval.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from src.data.indicators import IndicatorEngine
from src.data.levels import LevelCalculator
from src.data.patterns import PatternDetector
from src.data.market_data import MarketDataFetcher

logger = logging.getLogger(__name__)


@dataclass
class StockDataPack:
    """Complete pre-computed data for a single stock."""
    symbol: str
    exchange: str = "NSE"

    # Raw data
    daily_df: Optional[pd.DataFrame] = None
    intraday_df: Optional[pd.DataFrame] = None

    # Live quote
    ltp: float = 0.0
    day_open: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    day_close: float = 0.0
    prev_close: float = 0.0
    volume: int = 0
    change_pct: float = 0.0

    # Pre-computed
    indicators: dict = field(default_factory=dict)
    levels: dict = field(default_factory=dict)
    patterns: list = field(default_factory=list)
    volume_stats: dict = field(default_factory=dict)
    range_52w: dict = field(default_factory=dict)
    vwap: Optional[float] = None

    # Metadata
    last_updated: Optional[datetime] = None
    sector: str = ""


class DataWarehouse:
    """
    Central data store for the entire tradeable universe.
    Collects, computes, and caches all data for instant retrieval.
    """

    def __init__(
        self,
        market_data: MarketDataFetcher,
        indicator_engine: IndicatorEngine,
        level_calculator: LevelCalculator,
        pattern_detector: PatternDetector,
        config: dict,
    ):
        self.market_data = market_data
        self.indicator_engine = indicator_engine
        self.level_calculator = level_calculator
        self.pattern_detector = pattern_detector
        self.config = config

        self._data: dict[str, StockDataPack] = {}
        self._sector_map: dict[str, str] = {}
        self._boot_complete = False
        self._daily_candles_count = config.get("ai", {}).get("daily_candles_count", 15)

    def boot(
        self, universe: list[str], sector_map: dict[str, str] = None
    ) -> None:
        """
        Boot sequence: fetch daily candles and compute indicators for
        the entire universe. Called at 8:33 AM.
        """
        logger.info(f"DataWarehouse boot: loading data for {len(universe)} stocks...")
        start = time.time()

        if sector_map:
            self._sector_map = sector_map

        total = len(universe)
        success = 0
        failed = 0

        for i, symbol in enumerate(universe):
            try:
                pack = self._load_stock(symbol)
                if pack and pack.daily_df is not None:
                    self._data[symbol] = pack
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to load {symbol}: {e}")
                failed += 1

            # Progress logging every 50 stocks
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start
                logger.info(
                    f"  Progress: {i + 1}/{total} ({success} ok, {failed} failed) "
                    f"[{elapsed:.0f}s elapsed]"
                )

        elapsed = time.time() - start
        self._boot_complete = True
        logger.info(
            f"DataWarehouse boot complete: {success}/{total} stocks loaded "
            f"in {elapsed:.1f}s ({failed} failed)"
        )

    def _load_stock(self, symbol: str, exchange: str = "NSE") -> Optional[StockDataPack]:
        """Load and compute all data for a single stock."""
        pack = StockDataPack(symbol=symbol, exchange=exchange)
        pack.sector = self._sector_map.get(symbol, "")

        # Fetch daily candles
        pack.daily_df = self.market_data.fetch_daily_candles(
            symbol, exchange, days=self._daily_candles_count + 200  # extra for indicator warmup
        )
        if pack.daily_df is None or pack.daily_df.empty:
            return None

        # Compute indicators
        pack.daily_df = self.indicator_engine.compute_all(pack.daily_df)
        pack.indicators = self.indicator_engine.get_latest_indicators(pack.daily_df)

        # Compute levels
        pack.levels = self.level_calculator.get_key_levels(pack.daily_df)

        # Detect patterns
        pack.patterns = self.pattern_detector.detect_patterns(pack.daily_df)

        # Volume stats
        pack.volume_stats = self.market_data.compute_volume_stats(pack.daily_df)

        # 52-week range from the daily data we already have
        if len(pack.daily_df) >= 200:
            df_52w = pack.daily_df.tail(252)  # ~1 year of trading days
            pack.range_52w = {
                "high_52w": float(df_52w["high"].max()),
                "low_52w": float(df_52w["low"].min()),
            }

        pack.last_updated = datetime.now()
        return pack

    def refresh_quotes(self, universe: list[str]) -> None:
        """Update live quotes for all stocks in the universe."""
        quotes = self.market_data.fetch_bulk_quotes(universe)

        for symbol, quote in quotes.items():
            if symbol in self._data:
                pack = self._data[symbol]
                pack.ltp = quote.get("last_price", 0)
                ohlc = quote.get("ohlc", {})
                pack.day_open = ohlc.get("open", 0)
                pack.day_high = ohlc.get("high", 0)
                pack.day_low = ohlc.get("low", 0)
                pack.day_close = ohlc.get("close", 0)  # previous close in OHLC
                pack.prev_close = ohlc.get("close", 0)
                pack.volume = quote.get("volume", 0)

                if pack.prev_close and pack.prev_close > 0:
                    pack.change_pct = round(
                        ((pack.ltp - pack.prev_close) / pack.prev_close) * 100, 2
                    )
                pack.last_updated = datetime.now()

    def refresh_intraday(self, symbols: list[str] = None) -> None:
        """Refresh intraday candles and recompute intraday indicators."""
        if symbols is None:
            symbols = list(self._data.keys())

        for symbol in symbols:
            if symbol not in self._data:
                continue

            pack = self._data[symbol]
            pack.intraday_df = self.market_data.fetch_intraday_candles(symbol)

            if pack.intraday_df is not None and not pack.intraday_df.empty:
                pack.vwap = self.indicator_engine.compute_vwap(pack.intraday_df)

    # ─── RETRIEVAL ───

    def get_stock_data(self, symbol: str) -> Optional[StockDataPack]:
        """Get complete pre-computed data for one stock."""
        return self._data.get(symbol)

    def get_all_quotes(self) -> dict[str, dict]:
        """Get live quote data for all stocks."""
        result = {}
        for symbol, pack in self._data.items():
            result[symbol] = {
                "ltp": pack.ltp,
                "change_pct": pack.change_pct,
                "volume": pack.volume,
                "day_open": pack.day_open,
                "day_high": pack.day_high,
                "day_low": pack.day_low,
                "prev_close": pack.prev_close,
                "sector": pack.sector,
            }
        return result

    def get_loaded_symbols(self) -> list[str]:
        """Return list of symbols that have been loaded."""
        return list(self._data.keys())

    # ─── AGGREGATIONS FOR MARKET PULSE ───

    def get_top_gainers(self, n: int = 10) -> list[dict]:
        """Top N gainers by % change."""
        stocks = [
            {"symbol": s, "change_pct": p.change_pct, "ltp": p.ltp,
             "volume_ratio": p.volume_stats.get("volume_ratio", 0),
             "sector": p.sector}
            for s, p in self._data.items()
            if p.ltp > 0
        ]
        stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        return stocks[:n]

    def get_top_losers(self, n: int = 10) -> list[dict]:
        """Top N losers by % change."""
        stocks = [
            {"symbol": s, "change_pct": p.change_pct, "ltp": p.ltp,
             "volume_ratio": p.volume_stats.get("volume_ratio", 0),
             "sector": p.sector}
            for s, p in self._data.items()
            if p.ltp > 0
        ]
        stocks.sort(key=lambda x: x["change_pct"])
        return stocks[:n]

    def get_volume_surges(self, n: int = 10) -> list[dict]:
        """Top N stocks by volume ratio (today vs 20-day avg)."""
        stocks = [
            {"symbol": s, "change_pct": p.change_pct, "ltp": p.ltp,
             "volume_ratio": p.volume_stats.get("volume_ratio", 0),
             "sector": p.sector}
            for s, p in self._data.items()
            if p.volume_stats.get("volume_ratio", 0) > 0
        ]
        stocks.sort(key=lambda x: x["volume_ratio"], reverse=True)
        return stocks[:n]

    def get_52w_high_stocks(self, proximity_pct: float = 2.0) -> list[dict]:
        """Stocks within proximity_pct of their 52-week high."""
        result = []
        for symbol, pack in self._data.items():
            high_52w = pack.range_52w.get("high_52w", 0)
            if high_52w > 0 and pack.ltp > 0:
                pct_from_high = ((high_52w - pack.ltp) / high_52w) * 100
                if pct_from_high <= proximity_pct:
                    result.append({
                        "symbol": symbol,
                        "ltp": pack.ltp,
                        "high_52w": high_52w,
                        "pct_from_high": round(pct_from_high, 2),
                    })
        result.sort(key=lambda x: x["pct_from_high"])
        return result

    def get_52w_low_stocks(self, proximity_pct: float = 2.0) -> list[dict]:
        """Stocks within proximity_pct of their 52-week low."""
        result = []
        for symbol, pack in self._data.items():
            low_52w = pack.range_52w.get("low_52w", 0)
            if low_52w > 0 and pack.ltp > 0:
                pct_from_low = ((pack.ltp - low_52w) / low_52w) * 100
                if pct_from_low <= proximity_pct:
                    result.append({
                        "symbol": symbol,
                        "ltp": pack.ltp,
                        "low_52w": low_52w,
                        "pct_from_low": round(pct_from_low, 2),
                    })
        result.sort(key=lambda x: x["pct_from_low"])
        return result

    def get_gap_stocks(self, threshold_pct: float = 2.0) -> dict:
        """Stocks that gapped up or down more than threshold at open."""
        gap_up = []
        gap_down = []
        for symbol, pack in self._data.items():
            if pack.prev_close > 0 and pack.day_open > 0:
                gap_pct = ((pack.day_open - pack.prev_close) / pack.prev_close) * 100
                entry = {"symbol": symbol, "gap_pct": round(gap_pct, 2)}
                if gap_pct >= threshold_pct:
                    gap_up.append(entry)
                elif gap_pct <= -threshold_pct:
                    gap_down.append(entry)

        gap_up.sort(key=lambda x: x["gap_pct"], reverse=True)
        gap_down.sort(key=lambda x: x["gap_pct"])
        return {"gap_up": gap_up, "gap_down": gap_down}

    def get_market_breadth(self) -> dict:
        """Compute advance/decline/unchanged counts."""
        advances = 0
        declines = 0
        unchanged = 0
        for pack in self._data.values():
            if pack.change_pct > 0:
                advances += 1
            elif pack.change_pct < 0:
                declines += 1
            else:
                unchanged += 1

        ratio = round(advances / declines, 2) if declines > 0 else float("inf")
        return {
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
            "ad_ratio": ratio,
        }

    @property
    def is_booted(self) -> bool:
        return self._boot_complete
