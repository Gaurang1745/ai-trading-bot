import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Bundle the archived SQLite DB + agent JSON outputs into every API
  // route's serverless function. Next.js's static file-tracing won't pick
  // these up because they're opened via runtime paths, not import/require.
  // Without this, API routes fail with "SqliteError: unable to open
  // database file" on Vercel — the function bundle ships without data/.
  outputFileTracingIncludes: {
    "/api/*": ["./data/**"],
  },
};

export default nextConfig;
