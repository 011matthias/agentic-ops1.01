// Server-rendered login page for every gated client doc site. The proxy
// rewrites here (URL bar keeps the original doc path) with ?site=&from=.
// Form posts to /api/gate-unlock which validates the site code OR the
// master password and sets the HMAC grant cookie.

import { siteById, safeFromUrl, GATED_SITES } from "@/lib/gated-sites"

export const metadata = {
  title: "Documentation Access",
  robots: { index: false, follow: false },
}

type Props = {
  searchParams: Promise<{ site?: string; from?: string; err?: string }>
}

export default async function GateLoginPage({ searchParams }: Props) {
  const { site: siteId, from, err } = await searchParams
  // Fall back to the first registered site if the param is missing/unknown,
  // so the form still posts somewhere sane rather than 500-ing.
  const site = siteById(siteId) ?? GATED_SITES[0]
  const target = safeFromUrl(from, site)
  const showError = err === "1"

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#f8fafc",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <form
        action="/api/gate-unlock"
        method="POST"
        style={{ textAlign: "center", maxWidth: 360, padding: 24, width: "100%" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            margin: "0 auto 20px",
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 32 32"
            width="40"
            height="40"
          >
            <rect width="32" height="32" rx="7" fill="#2563eb" />
            <rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white" />
            <polygon points="18,8 23,16 18,24" fill="white" />
          </svg>
          <span style={{ fontSize: 22, letterSpacing: "-0.025em" }}>
            <span style={{ fontWeight: 700, color: "#0f172a" }}>Unpause</span>
            <span style={{ fontWeight: 700, color: "#2563eb" }}>AI</span>
          </span>
        </div>
        <h2
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: "#0f172a",
            marginBottom: 4,
          }}
        >
          {site.label}
        </h2>
        <p style={{ fontSize: 14, color: "#475569", marginBottom: 24 }}>
          Enter your access code to continue.
        </p>
        <input type="hidden" name="site" value={site.id} />
        <input type="hidden" name="from" value={target} />
        <div style={{ display: "flex", gap: 8 }}>
          <input
            name="code"
            type="password"
            placeholder="Access code"
            autoComplete="off"
            autoFocus
            required
            style={{
              flex: 1,
              padding: "10px 14px",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              fontSize: 15,
              background: "#ffffff",
              color: "#0f172a",
              outline: "none",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "10px 20px",
              border: "none",
              borderRadius: 8,
              background: "linear-gradient(135deg,#2563eb,#7c3aed)",
              color: "#fff",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            OK
          </button>
        </div>
        {showError && (
          <p style={{ color: "#dc2626", fontSize: 13, marginTop: 8 }}>
            Incorrect code. Please try again.
          </p>
        )}
      </form>
    </div>
  )
}
