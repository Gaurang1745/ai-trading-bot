import { NextResponse } from "next/server";
import { queryOne, queryAll } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const today = new Date().toISOString().split("T")[0];

    // Cash
    const cashRow = queryOne<{ balance: number }>(
      "SELECT balance FROM paper_cash WHERE id = 1"
    );
    const cash = cashRow?.balance ?? 0;

    // Holdings
    const holdings = queryAll<{ quantity: number; avg_price: number }>(
      "SELECT quantity, avg_price FROM paper_holdings WHERE quantity > 0"
    );
    const holdingsValue = holdings.reduce(
      (sum, h) => sum + h.quantity * h.avg_price,
      0
    );

    // Positions count
    const positions = queryAll(
      "SELECT * FROM paper_positions WHERE quantity != 0"
    );

    // Today's trades
    const tradesRow = queryOne<{ cnt: number; wins: number; losses: number; pnl: number }>(
      `SELECT COUNT(*) as cnt,
              SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
              COALESCE(SUM(pnl), 0) as pnl
       FROM trades WHERE DATE(timestamp) = ? AND mode = 'PAPER' AND status = 'COMPLETE'`,
      [today]
    );

    // AI cost today
    const costRow = queryOne<{ total: number }>(
      `SELECT COALESCE(SUM(
        input_cost_inr + output_cost_inr +
        COALESCE(cache_read_cost_inr, 0) + COALESCE(cache_creation_cost_inr, 0)
      ), 0) as total FROM llm_calls WHERE date = ?`,
      [today]
    );

    const wins = tradesRow?.wins ?? 0;
    const losses = tradesRow?.losses ?? 0;
    const totalTrades = wins + losses;

    return NextResponse.json({
      portfolio_value: cash + holdingsValue,
      cash,
      day_pnl: tradesRow?.pnl ?? 0,
      win_rate: totalTrades > 0 ? wins / totalTrades : 0,
      ai_cost_today: costRow?.total ?? 0,
      holdings_count: holdings.length,
      positions_count: positions.length,
      trades_today: tradesRow?.cnt ?? 0,
    });
  } catch (e) {
    return NextResponse.json(
      { error: String(e) },
      { status: 500 }
    );
  }
}
