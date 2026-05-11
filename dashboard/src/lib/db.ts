import Database from "better-sqlite3";
import path from "path";
import fs from "fs";
import os from "os";

// Resolve the DB by probing the candidate paths in priority order and
// picking the first one that exists. Vercel's outputFileTracingIncludes
// lands the data/ directory at the project root (cwd = /var/task) for
// some routes, while local-dev keeps the live bot's path. Probing avoids
// guessing wrong.
function resolveDbPath(): string {
  if (process.env.TRADING_DB_PATH) return process.env.TRADING_DB_PATH;
  const candidates = [
    path.resolve(process.cwd(), "data/trading_bot.db"),
    path.resolve(process.cwd(), "dashboard/data/trading_bot.db"),
    path.resolve(__dirname, "../../data/trading_bot.db"),
    path.resolve(__dirname, "../../../data/trading_bot.db"),
    path.resolve(__dirname, "../../../../data/trading_bot.db"),
    path.resolve(__dirname, "../../../../../data/trading_bot.db"),
    path.resolve(__dirname, "../../../../ai-trading-bot/data/trading_bot.db"),
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {
      // ignore
    }
  }
  return candidates[0]; // fall through; better-sqlite3 will throw with a useful message
}

// Vercel's serverless filesystem is read-only outside /tmp. better-sqlite3
// returns SQLITE_CANTOPEN even with readonly:true because SQLite still
// needs to create -shm / -wal sidecars (or check for their presence) in
// the DB's directory. Copy the DB to /tmp once per cold-start so SQLite
// has a writable directory to work in. /tmp persists for the lifetime of
// the warm function instance, so the copy is paid at most once per
// container.
function ensureWritableDb(srcPath: string): string {
  if (!process.env.VERCEL) return srcPath;
  const dst = path.join(os.tmpdir(), "trading_bot.db");
  if (!fs.existsSync(dst)) {
    fs.copyFileSync(srcPath, dst);
  }
  return dst;
}

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!db) {
    const dbPath = ensureWritableDb(resolveDbPath());
    db = new Database(dbPath, { readonly: true, fileMustExist: true });
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
