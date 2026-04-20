"""
Dhan API wrapper for market data.
Provides: live quotes, OHLC candles (5min, daily), instrument lookup.
Rate limits: 1 req/sec, 20K requests/day.
No order execution — paper trading only.
"""

import logging
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            self.calls.append(time.time())


class DhanDataClient:
    """
    Market data client using Dhan API.
    Provides the same interface as KiteClientWrapper (data methods only).
    Handles symbol-to-security_id translation internally.
    """

    def __init__(self, client_id: str, access_token: str, notifier=None):
        from dhanhq import dhanhq as DhanHQ
        self.dhan = DhanHQ(client_id=client_id, access_token=access_token)
        self.notifier = notifier

        # Rate limiter: 1 req/sec
        self._limiter = RateLimiter(max_calls=1, period_seconds=1.0)

        # Symbol mapping: "NSE:RELIANCE" -> security_id (int)
        self._symbol_to_secid: dict[str, int] = {}
        # Reverse: security_id -> "NSE:RELIANCE"
        self._secid_to_symbol: dict[int, str] = {}
        # Exchange mapping: "NSE" -> "NSE_EQ", "BSE" -> "BSE_EQ"
        self._exchange_to_segment = {
            "NSE": "NSE_EQ",
            "BSE": "BSE_EQ",
            "MCX": "MCX_COMM",
        }

    def _ensure_mapping(self, keys: list[str]) -> None:
        """Ensure all keys have security_id mappings. Load instruments if needed."""
        missing = [k for k in keys if k not in self._symbol_to_secid]
        if missing and not self._symbol_to_secid:
            logger.info("Loading Dhan instrument list for symbol mapping...")
            self._load_instrument_mapping()

    def _load_instrument_mapping(self) -> None:
        """Load the full instrument list and build symbol -> security_id mapping."""
        try:
            df = self.dhan.fetch_security_list(mode='compact')
            if df is None or df.empty:
                logger.error("Failed to fetch Dhan security list")
                return

            for _, row in df.iterrows():
                exchange = str(row.get("SEM_EXM_EXCH_ID", ""))
                symbol = str(row.get("SEM_TRADING_SYMBOL", ""))
                sec_id = int(row.get("SEM_SMST_SECURITY_ID", 0))
                segment = str(row.get("SEM_SEGMENT", ""))

                if not symbol or sec_id == 0:
                    continue

                # Only map equity segment
                if segment == "E":
                    key = f"{exchange}:{symbol}"
                    self._symbol_to_secid[key] = sec_id
                    self._secid_to_symbol[sec_id] = key

            logger.info(f"Loaded {len(self._symbol_to_secid)} symbol mappings from Dhan")
        except Exception as e:
            logger.error(f"Failed to load Dhan instrument mapping: {e}")

    def _get_secid(self, key: str) -> Optional[int]:
        """Get security_id for an 'EXCHANGE:SYMBOL' key."""
        self._ensure_mapping([key])
        return self._symbol_to_secid.get(key)

    def _get_segment(self, exchange: str) -> str:
        """Convert exchange name to Dhan segment constant."""
        return self._exchange_to_segment.get(exchange, "NSE_EQ")

    def _retry(self, func, max_retries: int = 3, delay: float = 1.0):
        """Retry with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Final retry failed: {e}")
                    raise
                wait = delay * (2 ** attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} after {wait:.1f}s: {str(e)[:100]}"
                )
                time.sleep(wait)

    # ─── QUOTES ───

    def get_quote(self, instruments: list[str]) -> dict:
        """
        Get OHLC quotes for instruments.
        instruments: list of "EXCHANGE:SYMBOL" strings, e.g. ["NSE:RELIANCE"]
        Returns dict in Kite-compatible format:
        {"NSE:RELIANCE": {"last_price": ..., "ohlc": {"open":..., "high":..., "low":..., "close":...}, "volume": ...}}
        """
        self._ensure_mapping(instruments)

        # Group by exchange segment
        seg_groups: dict[str, list[int]] = {}
        key_by_secid: dict[int, str] = {}

        for key in instruments:
            sec_id = self._symbol_to_secid.get(key)
            if not sec_id:
                continue
            exchange = key.split(":")[0]
            segment = self._get_segment(exchange)
            seg_groups.setdefault(segment, []).append(sec_id)
            key_by_secid[sec_id] = key

        if not seg_groups:
            return {}

        self._limiter.wait()
        resp = self._retry(lambda: self.dhan.quote_data(seg_groups))

        if resp.get("status") != "success":
            logger.error(f"Dhan quote_data failed: {resp.get('remarks', '')}")
            return {}

        data = resp.get("data", {})
        result = {}

        for segment, sec_data in data.items():
            for sec_id_str, quote in sec_data.items():
                sec_id = int(sec_id_str)
                key = key_by_secid.get(sec_id, "")
                if not key:
                    continue
                result[key] = {
                    "last_price": quote.get("last_price", 0),
                    "ohlc": quote.get("ohlc", {}),
                    "volume": quote.get("volume", 0),
                    "last_quantity": quote.get("last_quantity", 0),
                    "net_change": quote.get("net_change", 0),
                }

        return result

    def get_ltp(self, instruments: list[str]) -> dict:
        """
        Get last traded prices (lighter than full quote).
        Returns: {"NSE:RELIANCE": {"last_price": 2500.0}}
        """
        self._ensure_mapping(instruments)

        seg_groups: dict[str, list[int]] = {}
        key_by_secid: dict[int, str] = {}

        for key in instruments:
            sec_id = self._symbol_to_secid.get(key)
            if not sec_id:
                continue
            exchange = key.split(":")[0]
            segment = self._get_segment(exchange)
            seg_groups.setdefault(segment, []).append(sec_id)
            key_by_secid[sec_id] = key

        if not seg_groups:
            return {}

        self._limiter.wait()
        resp = self._retry(lambda: self.dhan.ticker_data(seg_groups))

        if resp.get("status") != "success":
            logger.error(f"Dhan ticker_data failed: {resp.get('remarks', '')}")
            return {}

        data = resp.get("data", {})
        result = {}

        for segment, sec_data in data.items():
            for sec_id_str, quote in sec_data.items():
                sec_id = int(sec_id_str)
                key = key_by_secid.get(sec_id, "")
                if not key:
                    continue
                result[key] = {"last_price": quote.get("last_price", 0)}

        return result

    # ─── HISTORICAL DATA ───

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str = "day",
    ) -> list[dict]:
        """
        Fetch historical candle data. Matches KiteClientWrapper interface.
        instrument_token is actually the Dhan security_id.
        interval: "day", "5minute", "15minute", etc.
        Returns list of dicts with: date, open, high, low, close, volume
        """
        security_id = str(instrument_token)

        if interval == "day":
            return self._fetch_daily(security_id, from_date, to_date)
        else:
            # Extract minute interval: "5minute" -> 5
            minute_interval = int(interval.replace("minute", ""))
            return self._fetch_intraday(security_id, from_date, to_date, minute_interval)

    def _fetch_daily(self, security_id: str, from_date: datetime, to_date: datetime) -> list[dict]:
        """Fetch daily candles from Dhan."""
        self._limiter.wait()
        resp = self._retry(lambda: self.dhan.historical_daily_data(
            security_id=security_id,
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            expiry_code=0,
        ))

        return self._parse_candle_response(resp)

    def _fetch_intraday(
        self, security_id: str, from_date: datetime, to_date: datetime, interval: int
    ) -> list[dict]:
        """Fetch intraday candles from Dhan."""
        self._limiter.wait()
        resp = self._retry(lambda: self.dhan.intraday_minute_data(
            security_id=security_id,
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
            interval=interval,
        ))

        return self._parse_candle_response(resp)

    def _parse_candle_response(self, resp: dict) -> list[dict]:
        """
        Parse Dhan's parallel-array candle format into list of dicts.
        Input: {"open": [...], "high": [...], "low": [...], "close": [...], "volume": [...], "timestamp": [...]}
        Output: [{"date": datetime, "open": float, "high": float, "low": float, "close": float, "volume": int}, ...]
        """
        if resp.get("status") != "success":
            logger.error(f"Dhan historical data failed: {resp.get('remarks', '')}")
            return []

        data = resp.get("data", {})
        if not data or not isinstance(data, dict):
            return []

        opens = data.get("open", [])
        highs = data.get("high", [])
        lows = data.get("low", [])
        closes = data.get("close", [])
        volumes = data.get("volume", [])
        timestamps = data.get("timestamp", [])

        if not timestamps:
            return []

        candles = []
        for i in range(len(timestamps)):
            dt = datetime.fromtimestamp(timestamps[i], tz=IST)
            candles.append({
                "date": dt,
                "open": opens[i] if i < len(opens) else 0,
                "high": highs[i] if i < len(highs) else 0,
                "low": lows[i] if i < len(lows) else 0,
                "close": closes[i] if i < len(closes) else 0,
                "volume": volumes[i] if i < len(volumes) else 0,
            })

        return candles

    def get_daily_candles(self, instrument_token: int, days: int = 30) -> list[dict]:
        """Fetch daily OHLCV candles for the last N days."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days + 5)  # buffer for weekends
        return self.get_historical_data(instrument_token, from_date, to_date, "day")

    def get_intraday_candles(
        self, instrument_token: int, interval: str = "5minute"
    ) -> list[dict]:
        """Fetch today's intraday candles."""
        today = datetime.now().replace(hour=9, minute=15, second=0)
        return self.get_historical_data(instrument_token, today, datetime.now(), interval)

    # ─── INSTRUMENTS ───

    def get_instruments(self, exchange: str = "NSE") -> list[dict]:
        """
        Get instrument list in Kite-compatible format.
        Returns list of dicts with: exchange, tradingsymbol, instrument_token, instrument_type, etc.
        """
        try:
            df = self.dhan.fetch_security_list(mode='compact')
            if df is None or df.empty:
                return []

            # Filter by exchange
            df = df[df["SEM_EXM_EXCH_ID"] == exchange]

            instruments = []
            for _, row in df.iterrows():
                segment = str(row.get("SEM_SEGMENT", ""))
                inst_type = str(row.get("SEM_EXCH_INSTRUMENT_TYPE", ""))

                # Determine if equity
                is_eq = segment == "E"

                instruments.append({
                    "exchange": exchange,
                    "tradingsymbol": str(row.get("SEM_TRADING_SYMBOL", "")),
                    "instrument_token": int(row.get("SEM_SMST_SECURITY_ID", 0)),
                    "instrument_type": "EQ" if is_eq else inst_type,
                    "segment": f"{exchange}-EQ" if is_eq else f"{exchange}-{segment}",
                    "tick_size": float(row.get("SEM_TICK_SIZE", 0.05)),
                    "lot_size": int(row.get("SEM_LOT_UNITS", 1)),
                    "name": str(row.get("SM_SYMBOL_NAME", "")),
                })

            return instruments
        except Exception as e:
            logger.error(f"Failed to fetch Dhan instruments: {e}")
            return []
