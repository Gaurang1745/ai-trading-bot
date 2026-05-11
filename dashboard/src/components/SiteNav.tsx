import Link from "next/link";

const navWrap: React.CSSProperties = {
  borderBottom: "1px solid var(--border)",
  background: "var(--background)",
  position: "sticky",
  top: 0,
  zIndex: 10,
};

const navInner: React.CSSProperties = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "0.85rem 1.5rem",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "1rem",
  flexWrap: "wrap",
};

const brand: React.CSSProperties = {
  fontFamily: "Georgia, 'Times New Roman', serif",
  fontWeight: 700,
  fontSize: "1rem",
  color: "var(--foreground)",
  textDecoration: "none",
  letterSpacing: "-0.01em",
};

const linksRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1.5rem",
  fontSize: "0.85rem",
};

const linkStyle: React.CSSProperties = {
  color: "var(--muted)",
  textDecoration: "none",
  borderBottom: "1px solid transparent",
  paddingBottom: "2px",
  transition: "color 0.15s, border-color 0.15s",
};

export default function SiteNav() {
  return (
    <nav style={navWrap} aria-label="Primary">
      <div style={navInner}>
        <Link href="/" style={brand}>
          AI Trading Bot
        </Link>
        <div style={linksRow}>
          <Link href="/" style={linkStyle}>
            Project
          </Link>
          <Link href="/dashboard" style={linkStyle}>
            Dashboard
          </Link>
          <Link href="/logs" style={linkStyle}>
            Logs
          </Link>
          <a
            href="https://github.com/Gaurang1745/ai-trading-bot"
            target="_blank"
            rel="noopener noreferrer"
            style={linkStyle}
          >
            Repo ↗
          </a>
        </div>
      </div>
    </nav>
  );
}
