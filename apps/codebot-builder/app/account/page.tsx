"use client";

import React, { useEffect, useMemo, useState } from "react";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";
const API_BASE = process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "/codebot/api";

type PortalOut = { url: string };
type CreditsOut = {
  availableCbt: number;
  monthlyCbtRemaining?: number;
  purchasedCbtRemaining?: number;
};

function _getToken(): string | null {
  try { return localStorage.getItem("access_token") || localStorage.getItem("codebot_access_token") || null; } catch { return null; }
}

async function apiJson<T>(
  path: string,
  init?: RequestInit
): Promise<{ ok: boolean; status: number; data?: T; text?: string }> {
  const token = _getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init?.headers as Record<string, string> || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers,
    ...init,
  });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = (await res.json().catch(() => undefined)) as T | undefined;
    return { ok: res.ok, status: res.status, data };
  }
  const text = await res.text().catch(() => "");
  return { ok: res.ok, status: res.status, text };
}

function fmt(n?: number) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "ok" | "warn" }) {
  const bg = tone === "ok" ? "rgba(34,197,94,0.12)" : tone === "warn" ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.06)";
  const color = tone === "ok" ? "rgba(134,239,172,1)" : tone === "warn" ? "rgba(253,224,71,1)" : "rgba(255,255,255,0.6)";
  return <span style={{ display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "4px 12px", fontSize: 11, fontWeight: 700, background: bg, color, whiteSpace: "nowrap" }}>{children}</span>;
}

const st = {
  page: { minHeight: "100vh", background: "var(--cb-bg, #0b0f14)", color: "white", padding: "48px 0" } as React.CSSProperties,
  wrap: { maxWidth: 960, margin: "0 auto", padding: "0 28px" } as React.CSSProperties,
  header: { marginBottom: 36, display: "flex", flexWrap: "wrap" as const, justifyContent: "space-between", alignItems: "flex-start", gap: 20 } as React.CSSProperties,
  h1: { fontSize: 26, fontWeight: 700, color: "white", margin: "8px 0 0", lineHeight: 1.2 } as React.CSSProperties,
  sub: { fontSize: 14, color: "rgba(255,255,255,0.5)", marginTop: 6 } as React.CSSProperties,
  pills: { display: "flex", gap: 8, marginBottom: 2 } as React.CSSProperties,
  btnGroup: { display: "flex", gap: 8, flexWrap: "wrap" as const } as React.CSSProperties,
  btnGhost: { height: 36, padding: "0 14px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.75)", fontSize: 13, fontWeight: 600, cursor: "pointer", textDecoration: "none", display: "inline-flex", alignItems: "center" } as React.CSSProperties,
  btnPrimary: { height: 36, padding: "0 14px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.92)", color: "rgba(0,0,0,0.9)", fontSize: 13, fontWeight: 600, cursor: "pointer", textDecoration: "none", display: "inline-flex", alignItems: "center" } as React.CSSProperties,
  card: { borderRadius: 14, background: "rgba(255,255,255,0.02)", boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)", marginBottom: 20, overflow: "hidden" } as React.CSSProperties,
  cardBody: { padding: 28 } as React.CSSProperties,
  errBox: { marginBottom: 20, padding: "14px 18px", borderRadius: 10, background: "rgba(255,77,77,0.08)", color: "#ff4d4d", fontSize: 14 } as React.CSSProperties,
  statLabel: { fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.04em", color: "rgba(255,255,255,0.4)", marginBottom: 8 } as React.CSSProperties,
  statVal: { fontSize: 36, fontWeight: 700, color: "white", lineHeight: 1.1 } as React.CSSProperties,
  statUnit: { fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,0.45)", marginLeft: 8 } as React.CSSProperties,
  statSub: { fontSize: 13, color: "rgba(255,255,255,0.5)", marginTop: 10 } as React.CSSProperties,
  miniStat: { borderRadius: 12, background: "rgba(0,0,0,0.15)", padding: 20 } as React.CSSProperties,
  miniLabel: { fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.04em", color: "rgba(255,255,255,0.4)", marginBottom: 6 } as React.CSSProperties,
  miniVal: { fontSize: 20, fontWeight: 700, color: "white" } as React.CSSProperties,
  miniSub: { fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 6 } as React.CSSProperties,
  grid3: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 } as React.CSSProperties,
  planRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 24, flexWrap: "wrap" as const } as React.CSSProperties,
  planName: { fontSize: 20, fontWeight: 700, color: "white", marginBottom: 4 } as React.CSSProperties,
  dotRow: { display: "flex", gap: 10, fontSize: 13, color: "rgba(255,255,255,0.7)", alignItems: "flex-start", lineHeight: 1.5 } as React.CSSProperties,
  dot: { width: 6, height: 6, borderRadius: "50%", background: "rgba(255,255,255,0.3)", marginTop: 6, flexShrink: 0 } as React.CSSProperties,
  sectionTitle: { fontSize: 16, fontWeight: 700, color: "white", marginBottom: 4 } as React.CSSProperties,
  sectionSub: { fontSize: 13, color: "rgba(255,255,255,0.45)", marginBottom: 16 } as React.CSSProperties,
  rateTable: { width: "100%", borderCollapse: "collapse" as const, fontSize: 13 } as React.CSSProperties,
  th: { textAlign: "left" as const, padding: "10px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.04em", color: "rgba(255,255,255,0.4)", borderBottom: "1px solid rgba(255,255,255,0.04)" } as React.CSSProperties,
  td: { padding: "10px 14px", color: "rgba(255,255,255,0.8)", borderBottom: "1px solid rgba(255,255,255,0.03)" } as React.CSSProperties,
  tdBold: { padding: "10px 14px", color: "white", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.03)" } as React.CSSProperties,
};

export default function AccountBillingPage() {
  const [credits, setCredits] = useState<CreditsOut | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  async function loadCredits() {
    setError("");
    const r = await apiJson<CreditsOut>("/credits");
    if (r.ok && r.data) setCredits(r.data);
    if (!r.ok) setError(`Couldn't load credits (HTTP ${r.status}).`);
    setLoaded(true);
  }

  useEffect(() => { loadCredits(); }, []);

  const available = credits?.availableCbt ?? 0;
  const monthly = credits?.monthlyCbtRemaining ?? 0;
  const purchased = credits?.purchasedCbtRemaining ?? 0;

  const dailyPace = useMemo(() => {
    if (!monthly) return "—";
    return `~${Math.ceil(monthly / 30)}`;
  }, [monthly]);

  async function openPortal() {
    setError("");
    setBusy("portal");
    try {
      const r = await apiJson<PortalOut>("/billing/portal");
      if (r.ok && r.data?.url) window.location.href = r.data.url;
      else setError(`Could not open Stripe portal (HTTP ${r.status}).`);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <div style={st.page}>
        <div style={st.wrap}>
          {/* Header */}
          <div style={st.header}>
            <div>
              <div style={st.pills}>
                <Pill tone="ok">Active</Pill>
                <Pill>Usage-Based</Pill>
              </div>
              <h1 style={st.h1}>Billing & Credits</h1>
              <div style={st.sub}>Pay for what you use. No fixed packs. Credits consumed per build.</div>
            </div>
            <div style={st.btnGroup}>
              <a href={`${BASE}/dashboard/`} style={st.btnGhost}>← Back to Dashboard</a>
              <button type="button" style={st.btnGhost} onClick={loadCredits} disabled={busy !== ""}>Refresh</button>
              <button type="button" style={st.btnPrimary} onClick={openPortal} disabled={busy === "portal"}>
                {busy === "portal" ? "Opening..." : "Open Stripe Portal"}
              </button>
            </div>
          </div>

          {error ? <div style={st.errBox}>{error}</div> : null}

          {/* Credits summary */}
          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <div style={st.statLabel}>Available Balance</div>
                  <div style={{ display: "flex", alignItems: "baseline" }}>
                    <span style={st.statVal}>{loaded ? fmt(available) : "—"}</span>
                    <span style={st.statUnit}>credits</span>
                  </div>
                  <div style={st.statSub}>
                    {loaded ? <>{fmt(monthly)} monthly &bull; {fmt(purchased)} purchased</> : "Loading..."}
                  </div>
                </div>

                <div style={st.miniStat}>
                  <div style={st.miniLabel}>Daily Pace</div>
                  <div style={st.miniVal}>{loaded ? `${dailyPace} / day` : "—"}</div>
                  <div style={st.miniSub}>To use your monthly allocation.</div>
                </div>
              </div>
            </div>
          </div>

          {/* How credits work */}
          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={st.sectionTitle}>How Credits Work</div>
              <div style={st.sectionSub}>Credits are consumed based on what you build. Larger builds use more credits.</div>
              <div style={{ display: "grid", gap: 8 }}>
                {[
                  "Monthly credits reset each billing cycle",
                  "Purchased credits never expire",
                  "Usage is metered per build, not per message",
                  "Buy additional credits any time from the Upgrade page",
                ].map((b) => (
                  <div key={b} style={st.dotRow}>
                    <div style={st.dot} />
                    <span>{b}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Plan */}
          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={st.planRow}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                    <span style={st.planName}>CodeBot Pro</span>
                    <Pill tone="ok">Active</Pill>
                  </div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {[
                      "Monthly credits included with your plan",
                      "Usage-based — only pay for what you build",
                      "Buy additional credits any time",
                      "Stripe-managed billing & invoices",
                    ].map((b) => (
                      <div key={b} style={st.dotRow}>
                        <div style={st.dot} />
                        <span>{b}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                  <a href={`${BASE}/account/upgrade`} style={st.btnPrimary}>Buy More Credits</a>
                  <button type="button" style={st.btnGhost} onClick={openPortal} disabled={busy === "portal"}>Manage Plan</button>
                </div>
              </div>
            </div>
          </div>

          <div style={{ height: 20 }} />
        </div>
      </div>
    </>
  );
}
