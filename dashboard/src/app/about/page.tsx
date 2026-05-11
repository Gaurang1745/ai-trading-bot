import Link from "next/link";

export const metadata = {
  title: "About — AI Trading Bot",
  description:
    "Architecture, design decisions, and live-experiment results of an autonomous AI trading bot for Indian equities.",
};

const C = {
  section: { marginBottom: "3rem" } as const,
  h2: {
    fontSize: "1.3rem",
    fontWeight: 700,
    marginTop: "2.5rem",
    marginBottom: "0.75rem",
    borderBottom: "1px solid var(--border)",
    paddingBottom: "0.4rem",
  } as const,
  h3: {
    fontSize: "1.05rem",
    fontWeight: 600,
    marginTop: "1.5rem",
    marginBottom: "0.5rem",
  } as const,
  p: {
    lineHeight: 1.65,
    marginBottom: "0.85rem",
    fontSize: "0.98rem",
  } as const,
  pre: {
    background: "var(--card-bg)",
    border: "1px solid var(--border)",
    borderRadius: "4px",
    padding: "0.85rem 1rem",
    overflowX: "auto" as const,
    fontSize: "0.78rem",
    lineHeight: 1.45,
    fontFamily: '"SF Mono", "Cascadia Code", "Fira Code", monospace',
  } as const,
  card: {
    background: "var(--card-bg)",
    border: "1px solid var(--border)",
    borderRadius: "4px",
    padding: "1rem 1.25rem",
    marginBottom: "0.75rem",
  } as const,
  badge: {
    display: "inline-block",
    padding: "0.15rem 0.5rem",
    fontSize: "0.72rem",
    border: "1px solid var(--border)",
    borderRadius: "3px",
    marginRight: "0.4rem",
    marginBottom: "0.3rem",
    background: "var(--card-bg)",
    fontFamily: '"SF Mono", "Cascadia Code", "Fira Code", monospace',
  } as const,
  statGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "0.75rem",
    marginTop: "1rem",
    marginBottom: "1.5rem",
  } as const,
  statCard: {
    background: "var(--card-bg)",
    border: "1px solid var(--border)",
    borderRadius: "4px",
    padding: "0.85rem 1rem",
  } as const,
  statLabel: {
    fontSize: "0.7rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    color: "var(--muted)",
    marginBottom: "0.3rem",
  } as const,
  statValue: {
    fontSize: "1.4rem",
    fontWeight: 700,
    fontFamily: '"SF Mono", "Cascadia Code", "Fira Code", monospace',
  } as const,
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={C.statCard}>
      <div style={C.statLabel}>{label}</div>
      <div style={C.statValue}>{value}</div>
      {sub && (
        <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export default function AboutPage() {
  return (
    <main
      style={{
        maxWidth: "860px",
        margin: "0 auto",
        padding: "2.5rem 1.5rem 4rem",
      }}
    >
      <header style={{ marginBottom: "1.5rem" }}>
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.5rem",
          }}
        >
          Project Showcase
        </div>
        <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.4rem" }}>
          AI Trading Bot — A 14-Session Experiment
        </h1>
        <p style={{ ...C.p, color: "var(--muted)", marginBottom: 0 }}>
          An autonomous Claude-driven paper-trading bot for Indian equity markets,
          built to test whether a multi-model AI pipeline with hard-coded guardrails
          can run a meaningful equity strategy end-to-end.{" "}
          <Link href="/" style={{ color: "var(--foreground)", textDecoration: "underline" }}>
            ← Back to dashboard
          </Link>
        </p>
      </header>

      <section style={C.section}>
        <div style={C.statGrid}>
          <Stat label="Trading sessions" value="14" sub="2026-04-22 → 2026-05-11" />
          <Stat label="Trades executed" value="160" sub="paper, CNC delivery" />
          <Stat label="Win rate" value="36.4%" sub="11W / 19L closed" />
          <Stat label="Cumulative P&L" value="−₹22,846" sub="−2.28% on ₹10L" />
          <Stat label="LLM calls" value="784" sub="Opus + Sonnet + Haiku" />
          <Stat label="AI spend" value="$170.85" sub="lifetime, 14 sessions" />
          <Stat label="Universe" value="510" sub="Nifty 500 + ETFs" />
          <Stat label="Agent runs" value="955" sub="4 autonomous agents" />
        </div>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>What it is</h2>
        <p style={C.p}>
          A fully autonomous trading bot that runs on its own — wakes up at 06:30 IST,
          refreshes its broker token, gathers overnight news, builds a watchlist of
          interesting names, runs deep-dive analysis on each, decides what to buy or
          sell, places paper orders through the broker API, monitors stop-losses through
          the day, exits intraday positions before the 3:20 PM auto-square-off, and
          reviews its own performance at EOD. Nothing in the loop is a human after
          the initial deployment.
        </p>
        <p style={C.p}>
          The interesting bit is <em>how</em> it makes decisions. Rather than one big
          monolithic prompt, three different Claude models specialize: <strong>Sonnet 4.6</strong>{" "}
          scans the market and picks the watchlist; <strong>Opus 4.7 (1M context)</strong>{" "}
          deep-dives every candidate with full pricing/technical/news data and emits
          structured BUY/SELL/MODIFY/EXIT decisions; <strong>Haiku 4.5</strong> handles
          cheap auxiliary tasks (news summarization, NSE ticker resolution). Cost vs
          capability is dialed in per call.
        </p>
        <p style={C.p}>
          Underneath the AI sits a hard-coded <strong>guardrail layer</strong> with 15+
          deterministic rules that validate every order before submission — position
          sizing, sector concentration, SL range, R:R floors, daily loss caps. The LLM
          is creative; the guardrails are the boring code that says &quot;no.&quot; That
          design assumption — that you cannot trust an LLM to be its own risk officer —
          is the single most important design choice in the whole system.
        </p>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>Architecture</h2>
        <pre style={C.pre}>{`main.py → Orchestrator
              ├── Broker Layer ─ Dhan client, TOTP-refreshed auth,
              │                  instrument cache
              ├── Data Layer ─── Market data fetcher (daily parquet
              │                  cache, intraday candles, bulk quotes),
              │                  indicators, universe filter (ASM/GSM,
              │                  T2T, liquidity)
              ├── News Layer ─── RSS aggregator, Haiku-filtered headlines
              ├── AI Layer ──── Anthropic SDK client, prompt formatter,
              │                  response parser, LLM call logger
              ├── Trading Layer
              │   ├── Portfolio State Manager  (mode-blind: paper / live
              │   │                             identical from Claude's POV)
              │   ├── Guardrail Engine  (15+ rules, hard-fail on violation)
              │   ├── Paper Broker / Execution Engine
              │   ├── Order Reconciler  (OHLC-based fills, no LTP fudging)
              │   ├── SL Health Check  (candle-based monitoring every 5min)
              │   └── MIS Auto-Exit  (4 stages: 15:00 / 15:05 / 15:10 / 15:12)
              ├── Agent Subprocess Layer
              │   ├── Pre-Market Research  (07:30 IST, web-search Claude Code)
              │   ├── Watchlist Research   (per-batch deep-dive)
              │   ├── Risk Monitor         (every 30min, adjusts overrides)
              │   └── Strategy Review      (16:00 daily, 09:00 Sat weekly)
              ├── Scheduler ── APScheduler cron, mon-fri, IST-aware
              ├── Database ─── SQLite WAL, 14 tables, 2 views
              └── Dashboard ── Next.js, better-sqlite3 read-only`}</pre>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>The two-stage AI pipeline</h2>
        <p style={C.p}>
          Every 30 minutes during market hours, the bot runs a Market Pulse cycle:
        </p>
        <ol style={{ ...C.p, paddingLeft: "1.5rem" }}>
          <li>
            <strong>Haiku 4.5</strong> filters overnight + intraday news headlines down
            to the relevant set — cheap, fast triage.
          </li>
          <li>
            <strong>Sonnet 4.6</strong> sees the news digest, market overview, top
            gainers/losers, sector heat, FII/DII flows, and emits a structured watchlist
            of ~15-25 candidates. ₹6/call, ~38 seconds.
          </li>
          <li>
            <strong>Symbol resolver</strong> (Haiku, universe-constrained): if Sonnet
            emits a long-form company name instead of an NSE ticker, Haiku is asked to
            map it back to the official ticker — validated against the actual instrument
            cache.
          </li>
          <li>
            <strong>Watchlist Research agents</strong> (Claude Code subprocesses) fan
            out in parallel — each batch deep-dives ~5 names with web search, gathering
            fundamentals, recent news, technical levels, and overhangs (regulatory,
            governance, earnings calendar).
          </li>
          <li>
            <strong>Opus 4.7 (1M-context)</strong> receives the assembled deep-dive
            pack for every watchlist symbol PLUS the entire existing book (holdings,
            open orders, SL/target state, recent decisions) and emits a structured
            JSON of decisions: <code>BUY / SELL / EXIT / MODIFY / HOLD / NO_ACTION</code>
            with confidence, R:R, SL, target, max_hold_days. ₹150-200/call, ~60 seconds.
          </li>
          <li>
            <strong>Response parser</strong> validates JSON shape, defaults missing
            fields, normalizes product types (CNC / MIS).
          </li>
          <li>
            <strong>Guardrail engine</strong> checks each order: position size,
            sector cap, SL band, R:R floor, per-position-risk budget, daily-loss
            limit, holding-cooldown, max working orders per symbol, short-sell
            legality. Failures are emitted as warnings (sometimes auto-corrected) or
            blocks (order dropped).
          </li>
          <li>
            <strong>Execution engine</strong> places the orders through the broker
            (paper-mode simulator that uses 5-minute OHLC to determine fills, not LTP
            snapshots — closer to real execution).
          </li>
        </ol>
        <p style={C.p}>
          Each call&apos;s system prompt, user prompt, response, token counts, and
          cost are persisted to disk under <code>logs/&lt;date&gt;/ai/</code> for
          per-call inspection. The dashboard exposes this whole tree.
        </p>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>Autonomous agents</h2>
        <p style={C.p}>
          The Market Pulse cycle is the primary trading loop, but four additional
          long-running agents run on their own cron schedules and have authority to
          mutate the bot&apos;s own configuration files:
        </p>
        <div style={C.card}>
          <strong>Pre-Market Research</strong> · 07:30 IST daily
          <p style={{ ...C.p, marginTop: "0.4rem", marginBottom: 0 }}>
            Web-search Claude Code subprocess. Pulls overnight global cues (US/EU/Asia
            close), FII/DII flows, earnings calendar, macro events, sector themes.
            Output is JSON with strict ticker-first formatting — long-form company
            names are rejected at the schema level.
          </p>
        </div>
        <div style={C.card}>
          <strong>Watchlist Research</strong> · per market-pulse cycle
          <p style={{ ...C.p, marginTop: "0.4rem", marginBottom: 0 }}>
            5-7 parallel subprocesses, each handling a batch of watchlist symbols.
            Web-search-equipped, each deep-dive output includes recent news, recent
            corporate actions, technical levels, key risk flags, sector context. The
            output schema is enforced by the parser; on missing fields, the symbol is
            dropped rather than fabricated.
          </p>
        </div>
        <div style={C.card}>
          <strong>Risk Monitor</strong> · every 30 min during market hours
          <p style={{ ...C.p, marginTop: "0.4rem", marginBottom: 0 }}>
            Opus subprocess. Reads the live portfolio + guardrail log + recent trade
            history. Has authority to <em>tighten or loosen</em> seven numeric
            overrides (max_position_pct, max_deployed_pct, max_sl_pct, min_confidence,
            min_risk_reward, max_sector_pct, daily_loss_limit_pct). Every change is
            justified in a per-decision changelog. The bot tunes its own risk knobs
            in response to its own behavior — and writes down why.
          </p>
        </div>
        <div style={C.card}>
          <strong>Strategy Review</strong> · 16:00 IST daily + 09:00 IST Saturday
          <p style={{ ...C.p, marginTop: "0.4rem", marginBottom: 0 }}>
            Opus subprocess with broader scope. Reads the full session&apos;s decisions,
            looks for structural failure modes (whipsaws, cluster stacks, sub-floor
            R:R admissions, panic exits), and can <em>edit the system prompt itself</em>
            — adding new behavioral rules referenced from in-session failures. Rules
            11-16 in the current system prompt (binary-event discipline, exit-is-final,
            governance DD, re-entry cooldown, same-session round-trip discipline,
            R:R-execution consistency) were all written by the bot reviewing its own
            mistakes.
          </p>
        </div>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>Tech stack</h2>
        <div style={{ marginBottom: "1rem" }}>
          <strong style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Backend</strong>
          <div style={{ marginTop: "0.4rem" }}>
            <span style={C.badge}>Python 3.11</span>
            <span style={C.badge}>APScheduler</span>
            <span style={C.badge}>SQLite WAL</span>
            <span style={C.badge}>pandas</span>
            <span style={C.badge}>pyarrow / parquet</span>
            <span style={C.badge}>Anthropic SDK</span>
            <span style={C.badge}>Dhan HQ Python SDK</span>
            <span style={C.badge}>pyotp</span>
            <span style={C.badge}>requests</span>
            <span style={C.badge}>pytest</span>
          </div>
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <strong style={{ fontSize: "0.85rem", color: "var(--muted)" }}>AI</strong>
          <div style={{ marginTop: "0.4rem" }}>
            <span style={C.badge}>claude-opus-4-7 (1M)</span>
            <span style={C.badge}>claude-sonnet-4-6</span>
            <span style={C.badge}>claude-haiku-4-5</span>
            <span style={C.badge}>Claude Code subprocess agents</span>
          </div>
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <strong style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Frontend</strong>
          <div style={{ marginTop: "0.4rem" }}>
            <span style={C.badge}>Next.js 16</span>
            <span style={C.badge}>React 19</span>
            <span style={C.badge}>better-sqlite3</span>
            <span style={C.badge}>TypeScript</span>
            <span style={C.badge}>Tailwind v4</span>
          </div>
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <strong style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Ops</strong>
          <div style={{ marginTop: "0.4rem" }}>
            <span style={C.badge}>AWS EC2 (ap-south-1)</span>
            <span style={C.badge}>systemd (bot + dashboard units)</span>
            <span style={C.badge}>GitHub Actions / PR review</span>
            <span style={C.badge}>Vercel (this dashboard)</span>
          </div>
        </div>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>The guardrail layer (why hard-coded rules)</h2>
        <p style={C.p}>
          A large frontier model is creative, articulate, and entirely capable of
          confidently producing a 15% position with a 7% stop-loss on a stock whose
          ticker doesn&apos;t exist. The guardrail layer assumes the LLM will hallucinate
          tickers, mis-state R:R math, leak shorts into a delivery product, breach
          sector caps, and emit MODIFY orders for positions it already closed — because
          all of these happened.
        </p>
        <p style={C.p}>
          Examples of rules that actually fired in production:
        </p>
        <ul style={{ ...C.p, paddingLeft: "1.5rem" }}>
          <li>
            <code>BLOCKED: Cannot short-sell in CNC. Holdings: 0, Order qty: 110</code>{" "}
            — Opus tried to SELL stocks it didn&apos;t own, in delivery mode, where
            short-selling is illegal.
          </li>
          <li>
            <code>BLOCKED: MODIFY for GLENMARK but no open position/holding</code> —
            tried to adjust SL on a position closed 26 seconds earlier. Recurring race.
          </li>
          <li>
            <code>BLOCKED: Confidence (0.0) below 0.60 threshold</code> — emitted
            structured-JSON trades with the confidence field unset (parser default of
            0.0), engine correctly rejected.
          </li>
          <li>
            <code>WARNING: SL too wide (4.4%). Max 4%.</code> — model attempted to
            justify exceeding the SL ceiling via per-position-risk math; the engine
            warned but didn&apos;t block, and the strategy reviewer later wrote a new
            rule into the system prompt to harden the case.
          </li>
        </ul>
        <p style={C.p}>
          Every guardrail event is logged to <code>guardrail_log</code> with the full
          order context. Across the experiment: <strong>2,519 events</strong>, of
          which 27 were hard blocks — roughly 1% block rate, mostly on the operational
          failure modes above, almost never on conviction-floor or sizing.
        </p>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>What I learned</h2>

        <h3 style={C.h3}>1. The bot held cash because of its own rules, not the engine</h3>
        <p style={C.p}>
          The deployment cap was set to 65% (later 80%), but average cash was 47-58%.
          Investigation showed zero guardrail blocks on conviction or deployment — the
          engine never said no. Opus simply chose to emit NO_ACTION on most candidates.
          The dominant cause was the system_prompt&apos;s conviction-tier sizing rule:
          {' "'}for trades 0.55-0.65, cap allocation at ~5%; reserve 10-15% for ≥0.70{'"'}.
          Opus generated almost exclusively 0.62-0.70 conviction signals — nothing
          above 0.70 in the entire experiment — so every admitted trade was sized at
          5%, and 9 holdings × 5% = 45% deployed. The cap was self-imposed
          calibration, not policy.
        </p>

        <h3 style={C.h3}>2. Confidence comes from Opus, not Sonnet</h3>
        <p style={C.p}>
          The natural intuition is &quot;maybe a smaller model would be less timid.&quot;
          But all 34 trading-decision calls per session ran on Opus 4.7 with full
          1M-context. The conviction distribution was Opus&apos;s calibrated read of
          a watchlist hand-picked for it. If the bot is being timid, the issue is the
          data being fed in, not the model evaluating it. Acted on this: the
          watchlist-research agents&apos; output schema was tightened to reduce
          ambiguous overhang noise.
        </p>

        <h3 style={C.h3}>3. The 06:30:00.000 TOTP race</h3>
        <p style={C.p}>
          On Day 11 the broker token refresh cron fired at exactly the wall-clock
          06:30:00.000. TOTP codes rotate every 30 seconds; the cron fired right at a
          window boundary, the bot generated a code, the request reached the broker
          server during the <em>next</em> 30-second window, and the broker rejected
          with <code>Invalid TOTP</code>. The bot then ran the entire trading day
          with no quotes, computed a phantom −₹5.37L &quot;loss&quot; on holdings
          showing <code>last_price = 0</code>, and emitted three panic-SELL orders
          (which were correctly rejected by the engine because the order price was
          0). Fix: retry once on Invalid TOTP after sleeping to 3 seconds past the
          next 30-second window boundary. One-line root cause, full-day outage.
        </p>

        <h3 style={C.h3}>4. The EOD cache stampede</h3>
        <p style={C.p}>
          Early in the experiment, the bot would re-fetch every stock&apos;s daily
          candle data on first boot of the trading day — 510 sequential Dhan API
          calls at the 1-req-per-2-second rate limit. Mornings consistently lost the
          first 22 minutes to this. Fix: warm the parquet cache at EOD (15:40) when
          there&apos;s nothing else competing for API quota; during market hours
          read from disk only. 22-minute boot → 1.1 seconds.
        </p>

        <h3 style={C.h3}>5. Same-session round-trips are usually research failures</h3>
        <p style={C.p}>
          When the bot EXITed a position it had BOUGHT 60 minutes earlier, in every
          observed case the exit citation was a pre-existing overhang that was
          knowable <em>before</em> entry — &quot;OMC refinery price-freeze
          overhang,&quot; &quot;single-asset operational binary,&quot; etc. The SL
          was sized to absorb normal intraday wobble; the intraday wobble was within
          budget; the model just got cold feet on information it already had. The
          fix is in the entry-research layer (catch the overhang before BUY), not the
          exit layer.
        </p>

        <h3 style={C.h3}>6. Risk-monitor ratchets are a one-way trap</h3>
        <p style={C.p}>
          Initially the risk monitor could only tighten overrides, never loosen. Over
          the first week the bot accumulated 7 tightenings (max_deployed_pct
          0.80→0.65, max_sl_pct 0.06→0.035, max_sector_pct 0.35→0.22, etc.) and got
          stuck — even when conditions improved, no agent had authority to revert.
          Fix: the strategy reviewer was given explicit loosen authority + a Day-10
          milestone for holistic stack review. Result: Day-10 review reverted 3 of 7
          overrides that had stopped binding.
        </p>

        <h3 style={C.h3}>7. The bot writes its own prompt</h3>
        <p style={C.p}>
          The most surprising thing operationally: rules 11-16 in the current system
          prompt — binary-event discipline, exit-is-final, governance DD, re-entry
          cooldown, same-session round-trip discipline, R:R-execution consistency —
          were all authored by the strategy-review agent <em>citing its own
          failures</em>. Each rule has a prior-failure-mode footnote that names the
          symbol, date, and exact reasoning that motivated the rule. The system
          prompt is no longer a static spec; it&apos;s a living changelog.
        </p>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>By the numbers</h2>
        <pre style={C.pre}>{`Backend (Python)
─────────────────────
  src/ files:           90+
  Lines of code:        ~14,000
  Database tables:      14
  Database rows total:  ~5,400
  Guardrail rules:      15+
  Scheduled jobs:       11 (incl. 4 MIS-exit stages)
  Agents:               4 autonomous + 5 inline LLM call types

Frontend (Next.js / TypeScript)
─────────────────────
  Pages:                3 (overview, logs, about)
  API routes:           9 (summary, trades, positions, agents,
                          llm-calls, performance, trade-history,
                          ai-logs, agent-outputs)

Experiment data
─────────────────────
  Trading sessions:     14
  Total trades:         160
  Closed positions:     30 (incl. 13 wind-down closes)
  Realized P&L:         −₹26,665
  Win rate:             36.4%
  LLM calls logged:     784
    └── Opus:           ~480
    └── Sonnet:         ~150
    └── Haiku:          ~154
  Token usage:          ~7.5M input + ~280K output (approx)
  AI spend (lifetime):  $170.85
  Subprocess agents:    955 runs
  Guardrail events:     2,519
  Portfolio snapshots:  147`}</pre>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>Honest take on the outcome</h2>
        <p style={C.p}>
          Net P&L was −₹22,846 (−2.28% on ₹10L paper capital over 14 sessions),
          dominated by a single −₹3,516 fat-tail loss on MAHABANK on Day 2 — ex-outlier
          the bot was roughly breakeven at +₹950. The win rate of 36.4% is below the
          ideal but the average winner was ~5x the average loser, so the math wasn&apos;t
          fundamentally broken; it was just under-deployed and over-conservative on
          sizing. The bot identified its own pathologies in the strategy reviews
          without being prompted to, which was the most genuinely interesting part to
          watch.
        </p>
        <p style={C.p}>
          The experiment ended not because of the P&L but because the iteration loop
          had become operational rather than directional — every change was a small
          turn-of-the-knob (timeouts, retry counts, prompt rules), not a fundamental
          rethink of the strategy. The right next step is a re-architected version
          that starts from {' "'}what should the watchlist look like?{'"'} rather than
          {' "'}what can we tweak about the existing watchlist?{'"'}
        </p>
      </section>

      <section style={C.section}>
        <h2 style={C.h2}>Links</h2>
        <ul style={{ ...C.p, paddingLeft: "1.5rem" }}>
          <li>
            <Link href="/" style={{ color: "var(--foreground)", textDecoration: "underline" }}>
              ← Live dashboard
            </Link>{" "}
            — final state of every trade, decision, and portfolio snapshot.
          </li>
          <li>
            <a
              href="https://github.com/Gaurang1745/ai-trading-bot"
              style={{ color: "var(--foreground)", textDecoration: "underline" }}
            >
              github.com/Gaurang1745/ai-trading-bot
            </a>{" "}
            — main code repository.
          </li>
          <li>
            <a
              href="https://github.com/Gaurang1745/ai-trading-bot/tree/experiment-archive"
              style={{ color: "var(--foreground)", textDecoration: "underline" }}
            >
              experiment-archive branch
            </a>{" "}
            — frozen SQLite database, agent outputs, and per-call logs.
          </li>
        </ul>
      </section>

      <footer
        style={{
          marginTop: "4rem",
          paddingTop: "1.5rem",
          borderTop: "1px solid var(--border)",
          fontSize: "0.8rem",
          color: "var(--muted)",
        }}
      >
        Experiment ran 2026-04-22 → 2026-05-11 on AWS EC2 (ap-south-1). Paper-trading
        mode; no real capital. Built with{" "}
        <a
          href="https://claude.com/claude-code"
          style={{ color: "var(--muted)", textDecoration: "underline" }}
        >
          Claude Code
        </a>
        .
      </footer>
    </main>
  );
}
