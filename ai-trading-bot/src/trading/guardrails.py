"""
Guardrail Validation Engine.
Every Claude decision is validated here BEFORE execution.
This is the most safety-critical component.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of guardrail validation for a single order."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    order: dict = field(default_factory=dict)  # potentially modified order


class GuardrailEngine:
    """
    Validates every trading decision against hard-coded rules.
    Claude's output MUST pass all checks before any order is placed.
    """

    def __init__(
        self,
        config: dict,
        portfolio_state,
        instrument_manager=None,
        notifier=None,
    ):
        self.config = config
        self.portfolio = portfolio_state
        self.instruments = instrument_manager
        self.notifier = notifier

        trading = config.get("trading", {})
        risk = config.get("risk", {})

        self._max_position_pct = trading.get("max_position_pct", 0.20)
        self._max_deployed_pct = trading.get("max_deployed_pct", 0.80)
        self._min_cash_buffer_pct = trading.get("min_cash_buffer_pct", 0.20)
        self._max_trades_per_day = trading.get("max_trades_per_day", 12)
        self._min_stock_price = trading.get("min_stock_price", 20)
        self._max_cnc_hold_days = trading.get("max_cnc_hold_days", 15)
        self._unwind_days = trading.get("unwind_phase_days", 5)
        self._no_new_mis_after = trading.get("no_new_mis_after", "14:30")

        self._daily_loss_limit_pct = risk.get("daily_loss_limit_pct", 0.03)
        self._drawdown_reduce_pct = risk.get("drawdown_reduce_pct", 0.10)
        self._drawdown_halt_pct = risk.get("drawdown_halt_pct", 0.15)
        self._default_sl_pct = risk.get("default_sl_pct", 0.02)
        self._min_sl_pct = risk.get("min_sl_pct", 0.005)
        self._max_sl_pct = risk.get("max_sl_pct", 0.05)
        self._min_confidence = risk.get("min_confidence", 0.50)
        self._duplicate_window = config.get("resilience", {}).get(
            "duplicate_order_window_min", 5
        )

        # ASM/GSM list (loaded externally)
        self._asm_gsm_list: set[str] = set()

    def set_asm_gsm_list(self, symbols: list[str]) -> None:
        """Update the ASM/GSM restricted list."""
        self._asm_gsm_list = set(symbols)

    def validate_order(self, order: dict) -> ValidationResult:
        """
        Validate a single order dict from Claude's response.
        Returns ValidationResult with is_valid, errors, warnings.
        The order may be modified (e.g., default SL/target applied).
        """
        errors = []
        warnings = []
        order = dict(order)  # work on a copy

        # Skip validation for non-actionable decisions
        action = order.get("action", "").upper()
        if action in ("NO_ACTION", "HOLD"):
            return ValidationResult(is_valid=True, order=order)

        # ─── INSTRUMENT CHECKS ───
        if order.get("exchange") not in ("NSE", "BSE"):
            errors.append(
                f"BLOCKED: Exchange must be NSE or BSE. Got: {order.get('exchange')}"
            )

        if order.get("product") not in ("CNC", "MIS"):
            errors.append(
                f"BLOCKED: Product must be CNC or MIS. Got: {order.get('product')}"
            )

        # ─── SYMBOL VALIDATION ───
        symbol = order.get("symbol", "")
        if self.instruments and not self.instruments.is_valid_symbol(symbol):
            errors.append(f"BLOCKED: Symbol {symbol} not found in instrument list")

        # ─── ASM/GSM CHECK ───
        if symbol in self._asm_gsm_list:
            errors.append(f"BLOCKED: {symbol} is on ASM/GSM restricted list")

        # ─── PRICE CHECK ───
        price = order.get("price", 0)
        if price and price < self._min_stock_price and order.get("order_type") == "LIMIT":
            errors.append(f"BLOCKED: Stock price INR {price} below INR {self._min_stock_price} threshold")

        # ─── SHORT SELLING CHECK (SEBI) ───
        tx_type = order.get("transaction_type", order.get("action", "")).upper()
        if tx_type in ("SELL", "EXIT"):
            if order.get("product") == "CNC":
                holdings_qty = self.portfolio.get_holdings_qty(symbol)
                order_qty = order.get("quantity", 0)
                if holdings_qty < order_qty:
                    errors.append(
                        f"BLOCKED: Cannot short-sell in CNC. "
                        f"Holdings: {holdings_qty}, Order qty: {order_qty}"
                    )

        # ─── POSITION SIZING ───
        portfolio_value = self.portfolio.total_value()
        ltp = order.get("price", 0) or self._get_ltp(symbol, order.get("exchange", "NSE"))
        qty = order.get("quantity", 0)
        position_value = ltp * qty if ltp and qty else 0

        max_position = portfolio_value * self._max_position_pct
        if position_value > max_position:
            errors.append(
                f"BLOCKED: Position value INR {position_value:,.0f} exceeds "
                f"{self._max_position_pct*100:.0f}% of portfolio (INR {max_position:,.0f})"
            )

        # ─── CASH BUFFER CHECK ───
        if tx_type == "BUY" and position_value > 0:
            cash = self.portfolio.get_available_cash()
            remaining_cash = cash - position_value
            min_cash = portfolio_value * self._min_cash_buffer_pct
            if remaining_cash < min_cash:
                errors.append(
                    f"BLOCKED: Order would breach {self._min_cash_buffer_pct*100:.0f}% cash buffer. "
                    f"Cash after: INR {remaining_cash:,.0f}, Min: INR {min_cash:,.0f}"
                )

        # ─── DAILY LOSS LIMIT ───
        daily_pnl = self.portfolio.get_daily_pnl()
        total_daily_loss = daily_pnl.get("realized", 0) + daily_pnl.get("unrealized", 0)
        daily_limit = portfolio_value * self._daily_loss_limit_pct
        if total_daily_loss < -daily_limit:
            errors.append(
                f"BLOCKED: Daily loss limit hit. "
                f"Current loss: INR {abs(total_daily_loss):,.0f}, "
                f"Limit: INR {daily_limit:,.0f}"
            )

        # ─── TRADE COUNT LIMIT ───
        trades_today = self.portfolio.trades_today_count()
        if trades_today >= self._max_trades_per_day:
            errors.append(
                f"BLOCKED: Max trades per day ({self._max_trades_per_day}) reached"
            )

        # ─── TIMING CHECKS ───
        now = datetime.now().time()
        mis_cutoff_parts = self._no_new_mis_after.split(":")
        mis_cutoff = time(int(mis_cutoff_parts[0]), int(mis_cutoff_parts[1]))

        if order.get("product") == "MIS" and tx_type == "BUY" and now > mis_cutoff:
            errors.append("BLOCKED: No new MIS orders after 2:30 PM IST")

        if now < time(9, 15) or now > time(15, 30):
            if not (now >= time(9, 0) and order.get("product") == "CNC"):
                errors.append("BLOCKED: Outside market hours")

        # ─── STOP-LOSS CHECK ───
        if not order.get("stop_loss"):
            if tx_type == "BUY":
                order["stop_loss"] = round(ltp * (1 - self._default_sl_pct), 2) if ltp else None
            elif tx_type in ("SELL", "EXIT"):
                order["stop_loss"] = round(ltp * (1 + self._default_sl_pct), 2) if ltp else None
            warnings.append(
                f"WARNING: No stop-loss specified. Applied default {self._default_sl_pct*100:.0f}% SL."
            )

        # ─── STOP-LOSS RANGE CHECK ───
        sl = order.get("stop_loss", 0)
        if sl and ltp and ltp > 0:
            if tx_type == "BUY":
                sl_pct = (ltp - sl) / ltp
            else:
                sl_pct = (sl - ltp) / ltp

            if sl_pct < self._min_sl_pct:
                warnings.append(
                    f"WARNING: SL too tight ({sl_pct:.1%}). Min {self._min_sl_pct*100:.1f}%."
                )
            if sl_pct > self._max_sl_pct:
                warnings.append(
                    f"WARNING: SL too wide ({sl_pct:.1%}). Max {self._max_sl_pct*100:.0f}%."
                )

        # ─── TARGET CHECK ───
        if not order.get("target"):
            default_target_pct = 0.03
            if tx_type == "BUY":
                order["target"] = round(ltp * (1 + default_target_pct), 2) if ltp else None
            elif tx_type in ("SELL", "EXIT"):
                order["target"] = round(ltp * (1 - default_target_pct), 2) if ltp else None
            warnings.append("WARNING: No target specified. Applied default 3% target.")

        # ─── CONFIDENCE CHECK ───
        confidence = order.get("confidence", 0)
        if confidence < self._min_confidence:
            errors.append(
                f"BLOCKED: Confidence ({confidence}) below {self._min_confidence} threshold"
            )

        # ─── EXPERIMENT PHASE CHECK ───
        exp = self.config.get("experiment", {})
        start_str = exp.get("start_date", "2026-03-01")
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        duration = exp.get("duration_days", 30)
        from datetime import timedelta
        end_date = start_date + timedelta(days=duration)
        today = datetime.now().date()
        # Count remaining trading days
        trading_days_left = 0
        d = today
        while d <= end_date:
            if d.weekday() < 5:
                trading_days_left += 1
            d += timedelta(days=1)

        if trading_days_left <= self._unwind_days:
            if order.get("product") == "CNC" and tx_type == "BUY":
                errors.append(
                    f"BLOCKED: In unwind phase (last {self._unwind_days} trading days). "
                    f"No new CNC positions allowed."
                )

        # ─── CNC HOLD DURATION CHECK ───
        max_hold = order.get("max_hold_days", 0)
        if order.get("product") == "CNC" and max_hold > self._max_cnc_hold_days:
            warnings.append(
                f"WARNING: Max hold days ({max_hold}) exceeds {self._max_cnc_hold_days}-day limit. "
                f"Capping."
            )
            order["max_hold_days"] = self._max_cnc_hold_days

        # ─── DRAWDOWN CHECK ───
        starting_capital = exp.get("starting_capital", 100000)
        total_return_pct = (portfolio_value - starting_capital) / starting_capital
        if total_return_pct < -self._drawdown_halt_pct:
            errors.append(
                f"BLOCKED: {self._drawdown_halt_pct*100:.0f}% drawdown breached. Trading halted."
            )
        elif total_return_pct < -self._drawdown_reduce_pct:
            if order.get("product") == "CNC":
                errors.append(
                    f"BLOCKED: {self._drawdown_reduce_pct*100:.0f}% drawdown. CNC not allowed."
                )
            order["quantity"] = max(1, order.get("quantity", 0) // 2)
            warnings.append(
                f"WARNING: {self._drawdown_reduce_pct*100:.0f}% drawdown. Position size halved."
            )

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            order=order,
        )

        # Log result
        if not result.is_valid:
            logger.warning(
                f"Guardrail BLOCKED {symbol} {tx_type}: {'; '.join(errors)}"
            )
        if warnings:
            logger.info(f"Guardrail warnings for {symbol}: {'; '.join(warnings)}")

        return result

    def validate_all_decisions(self, decisions: list[dict]) -> list[ValidationResult]:
        """Validate a list of decisions from Claude's response."""
        results = []
        for decision in decisions:
            result = self.validate_order(decision)
            results.append(result)
        return results

    def _get_ltp(self, symbol: str, exchange: str = "NSE") -> float:
        """Get LTP for a symbol from portfolio state data."""
        # Try to get from portfolio's cached quotes
        quotes = getattr(self.portfolio, "_last_quotes", {})
        key = f"{exchange}:{symbol}"
        if key in quotes:
            return quotes[key].get("last_price", 0)
        return 0
