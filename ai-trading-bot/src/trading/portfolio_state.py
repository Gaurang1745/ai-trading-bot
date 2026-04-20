"""
Portfolio State Manager.
Provides portfolio data from paper trading tables.
Claude NEVER knows this is paper trading.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


class PortfolioStateManager:
    """
    Unified interface to portfolio data for paper trading.
    The prompt builder ONLY interacts with this class.
    """

    def __init__(self, data_client, db, config: dict):
        self.data_client = data_client
        self.db = db
        self._starting_capital = config.get("experiment", {}).get("starting_capital", 100000)

    # ─── CORE ACCESSORS ───

    def get_holdings(self) -> list[dict]:
        """
        Returns CNC holdings.
        Format: [{symbol, quantity, avg_price, last_price, pnl, pnl_pct, days_held, ...}]
        """
        try:
            rows = self.db.fetchall(
                "SELECT * FROM paper_holdings WHERE quantity > 0"
            )
            holdings = []
            for row in rows:
                symbol = row["symbol"]
                qty = row["quantity"]
                avg = row["avg_price"]
                ltp = self._get_ltp(symbol)
                pnl = (ltp - avg) * qty if ltp else 0
                pnl_pct = ((ltp - avg) / avg * 100) if avg > 0 and ltp else 0
                holdings.append({
                    "symbol": symbol,
                    "exchange": (row["exchange"] if "exchange" in row.keys() else "NSE"),
                    "quantity": qty,
                    "avg_price": avg,
                    "last_price": ltp,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "days_held": 0,
                    "stop_loss": 0,
                    "target": 0,
                })
            return holdings
        except Exception as e:
            logger.error(f"Failed to get paper holdings: {e}")
            return []

    def get_positions(self) -> list[dict]:
        """
        Returns open MIS positions.
        Format: [{symbol, side, quantity, entry, ltp, pnl, pnl_pct, stop_loss, target, ...}]
        """
        try:
            rows = self.db.fetchall(
                "SELECT * FROM paper_positions WHERE quantity != 0 AND product = 'MIS'"
            )
            positions = []
            for row in rows:
                symbol = row["symbol"]
                qty = row["quantity"]
                entry = row["entry_price"]
                ltp = self._get_ltp(symbol)
                side = "BUY" if qty > 0 else "SELL"
                pnl = (ltp - entry) * abs(qty) if ltp else 0
                if side == "SELL":
                    pnl = -pnl
                pnl_pct = (pnl / (entry * abs(qty)) * 100) if entry > 0 else 0
                positions.append({
                    "symbol": symbol,
                    "exchange": "NSE",
                    "side": side,
                    "quantity": abs(qty),
                    "entry": entry,
                    "ltp": ltp,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "stop_loss": (row["stop_loss"] if "stop_loss" in row.keys() else 0) or 0,
                    "target": (row["target"] if "target" in row.keys() else 0) or 0,
                })
            return positions
        except Exception as e:
            logger.error(f"Failed to get paper positions: {e}")
            return []

    def get_available_cash(self) -> float:
        """Returns available cash for trading."""
        try:
            row = self.db.fetchone(
                "SELECT balance FROM paper_cash WHERE id = 1"
            )
            cash = row["balance"] if row else self._starting_capital
            reserved = self.db.get_total_reserved_cash()
            return max(0, cash - reserved)
        except Exception as e:
            logger.error(f"Failed to get paper cash: {e}")
            return self._starting_capital

    def get_daily_pnl(self) -> dict:
        """Returns today's P&L breakdown: {realized, unrealized}."""
        try:
            today = date.today().isoformat()
            row = self.db.fetchone(
                """SELECT COALESCE(SUM(pnl), 0) as realized
                   FROM trades WHERE DATE(timestamp) = ? AND status = 'COMPLETE'
                   AND mode = 'PAPER'""",
                (today,),
            )
            realized = row["realized"] if row else 0

            unrealized = 0
            for h in self.get_holdings():
                unrealized += h.get("pnl", 0)
            for p in self.get_positions():
                unrealized += p.get("pnl", 0)

            return {"realized": round(realized, 2), "unrealized": round(unrealized, 2)}
        except Exception as e:
            logger.error(f"Failed to get paper P&L: {e}")
            return {"realized": 0, "unrealized": 0}

    def total_value(self) -> float:
        """Returns total portfolio value (cash + holdings value)."""
        cash = self.get_available_cash()
        holdings_value = sum(
            h.get("last_price", 0) * h.get("quantity", 0)
            for h in self.get_holdings()
        )
        return cash + holdings_value

    def trades_today_count(self) -> int:
        """Returns number of trades placed today."""
        return self.db.count_trades_today(mode="PAPER")

    def get_holdings_qty(self, symbol: str) -> int:
        """Get holdings quantity for a specific symbol."""
        holdings = self.get_holdings()
        for h in holdings:
            if h.get("symbol") == symbol:
                return h.get("quantity", 0)
        return 0

    # ─── FULL STATE FOR PROMPTS ───

    def get_portfolio_state(self) -> dict:
        """
        Build the complete portfolio state dict for prompt formatting.
        This is the main interface used by PromptFormatter.
        """
        holdings = self.get_holdings()
        positions = self.get_positions()
        cash = self.get_available_cash()
        daily_pnl = self.get_daily_pnl()
        total = self.total_value()

        return {
            "total_value": total,
            "cash": cash,
            "daily_pnl": daily_pnl,
            "holdings": holdings,
            "mis_positions": positions,
            "trades_today": self.trades_today_count(),
            "starting_capital": self._starting_capital,
        }

    def get_existing_positions_for_prompt(self) -> list[dict]:
        """
        Build position details for the EXISTING POSITION UPDATES section.
        Merges holdings + MIS positions into a single list.
        """
        result = []

        for h in self.get_holdings():
            result.append({
                "symbol": h.get("symbol", ""),
                "product": "CNC",
                "side": "BUY",
                "quantity": h.get("quantity", 0),
                "entry": h.get("avg_price", 0),
                "ltp": h.get("last_price", 0),
                "pnl": h.get("pnl", 0),
                "pnl_pct": h.get("pnl_pct", 0),
                "days_held": h.get("days_held", 0),
                "stop_loss": h.get("stop_loss", 0),
                "target": h.get("target", 0),
            })

        for p in self.get_positions():
            result.append({
                "symbol": p.get("symbol", ""),
                "product": "MIS",
                "side": p.get("side", "BUY"),
                "quantity": p.get("quantity", 0),
                "entry": p.get("entry", 0),
                "ltp": p.get("ltp", 0),
                "pnl": p.get("pnl", 0),
                "pnl_pct": p.get("pnl_pct", 0),
                "days_held": 0,
                "stop_loss": p.get("stop_loss", 0),
                "target": p.get("target", 0),
            })

        return result

    def get_held_symbols(self) -> list[str]:
        """Get list of symbols currently held (CNC + MIS)."""
        symbols = set()
        for h in self.get_holdings():
            if h.get("quantity", 0) > 0:
                symbols.add(h.get("symbol", ""))
        for p in self.get_positions():
            if p.get("quantity", 0) != 0:
                symbols.add(p.get("symbol", ""))
        return list(symbols)

    def total_return_pct(self) -> float:
        """Compute total return percentage since experiment start."""
        total = self.total_value()
        if self._starting_capital > 0:
            return (total - self._starting_capital) / self._starting_capital
        return 0.0

    # ─── HELPERS ───

    def _get_ltp(self, symbol: str) -> float:
        """Get live LTP for a symbol via data client."""
        if self.data_client:
            try:
                key = f"NSE:{symbol}"
                quote = self.data_client.get_ltp([key])
                return quote.get(key, {}).get("last_price", 0)
            except Exception:
                pass
        return 0
