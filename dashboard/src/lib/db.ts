import Database from "better-sqlite3";
import path from "path";

// Path resolution: env override → cwd-based default (Vercel deploy)
// → relative-from-source default (local dev against the bot's data dir).
const DB_PATH =
  process.env.TRADING_DB_PATH ||
  (process.env.VERCEL
    ? path.resolve(process.cwd(), "data/trading_bot.db")
    : path.resolve(__dirname, "../../../../ai-trading-bot/data/trading_bot.db"));

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!db) {
    // Open read-only without WAL. Vercel's serverless filesystem is
    // read-only outside /tmp; WAL would try to create -wal/-shm files
    // alongside the DB and fail. For an archive deployment the bot is
    // not writing, so WAL is not needed.
    db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
  }
  return db;
}

export function queryAll<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = []
): T[] {
  return getDb().prepare(sql).all(...params) as T[];
}

export function queryOne<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = []
): T | undefined {
  return getDb().prepare(sql).get(...params) as T | undefined;
}
