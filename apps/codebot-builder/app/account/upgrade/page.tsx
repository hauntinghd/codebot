"use client";

import React, { useEffect, useMemo, useState } from "react";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";
const API_BASE = process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "/codebot/api";

type PortalOut = { url: string };
type CreditsOut = { availableCbt: number; monthlyCbtRemaining?: number; purchasedCbtRemaining?: number };
type MeOut = { id: string; email: string; is_admin: boolean; subscription_status?: string; plan?: string; current_period_end?: number; credits_remaining?: number | null; display_name?: string | null };

async function apiJson<T>(path: string, init?: RequestInit): Promise<{ ok: boolean; status: number; data?: T; text?: string }> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) }, ...init });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) { const data = (await res.json().catch(() => undefined)) as T | undefined; return { ok: res.ok, status: res.status, data }; }
  return { ok: res.ok, status: res.status, text: await res.text().catch(() => "") };
}

function fmt(n?: number) { if (typeof n !== "number" || !Number.isFinite(n)) return "—"; return n.toLocaleString(); }

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "ok" | "warn" }) {
  const bg = tone === "ok" ? "rgba(34,197,94,0.12)" : tone === "warn" ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.06)";
  const color = tone === "ok" ? "rgba(134,239,172,1)" : tone === "warn" ? "rgba(253,224,71,1)" : "rgba(255,255,255,0.6)";
  return <span style={{ display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "4px 12px", fontSize: 11, fontWeight: 700, background: bg, color, whiteSpace: "nowrap" }}>{children}</span>;
}

function fmtDate(sec?: number): string {
  if (!sec || !Number.isFinite(sec)) return "—";
  try { return new Date(sec * 1000).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" }); } catch { return "—"; }
}

const CREDIT_TIERS = [
  { credits: 500, tag: null },
  { credits: 2000, tag: "Popular" },
  { credits: 5000, tag: "Best Value" },
] as const;

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
  grid3: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 } as React.CSSProperties,
  miniStat: { borderRadius: 12, background: "rgba(0,0,0,0.15)", padding: 20 } as React.CSSProperties,
  miniLabel: { fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.04em", color: "rgba(255,255,255,0.4)", marginBottom: 6 } as React.CSSProperties,
  miniVal: { fontSize: 20, fontWeight: 700, color: "white" } as React.CSSProperties,
  miniSub: { fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 6 } as React.CSSProperties,
  sectionTitle: { fontSize: 18, fontWeight: 700, color: "white", marginBottom: 6 } as React.CSSProperties,
  sectionSub: { fontSize: 13, color: "rgba(255,255,255,0.45)", marginBottom: 20 } as React.CSSProperties,
  tierCard: (hl: boolean) => ({ borderRadius: 14, background: hl ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.12)", padding: 24, position: "relative" as const, display: "flex", flexDirection: "column" as const, gap: 14 }) as React.CSSProperties,
  tierTag: { position: "absolute" as const, top: 12, right: 12 } as React.CSSProperties,
  dotRow: { display: "flex", gap: 10, fontSize: 13, color: "rgba(255,255,255,0.7)", alignItems: "flex-start", lineHeight: 1.5 } as React.CSSProperties,
  dot: { width: 5, height: 5, borderRadius: "50%", background: "rgba(255,255,255,0.3)", marginTop: 7, flexShrink: 0 } as React.CSSProperties,
};

export default function UpgradePage() {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [credits, setCredits] = useState<CreditsOut | null>(null);
  const [me, setMe] = useState<MeOut | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadCredits() { const res = await apiJson<CreditsOut>("/credits/balance"); if (res.ok && res.data) setCredits(res.data); setLoaded(true); }
  async function loadMe() { const who = await apiJson<MeOut>("/auth/whoami"); if (who.ok && who.data) { setMe(who.data); return; } const prof = await apiJson<MeOut>("/profile"); if (prof.ok && prof.data) { setMe(prof.data); return; } setMe(null); }
  async function refreshAll() { await Promise.all([loadMe(), loadCredits()]); }

  async function openPortal() {
    setError(""); setBusy("portal");
    try { const r = await apiJson<PortalOut>("/billing/portal"); if (r.ok && r.data?.url) { window.location.href = r.data.url; return; } setError(`Stripe portal: ${(r.data as any)?.error || r.text || `HTTP ${r.status}`}`); }
    finally { setBusy(""); }
  }

  async function buyCredits(tier: typeof CREDIT_TIERS[number]) {
    setError(""); setBusy(`buy-${tier.credits}`);
    try {
      const r = await apiJson<{ url?: string }>("/billing/credits/checkout", { method: "POST", body: JSON.stringify({ credits: tier.credits }) });
      if (r.ok && (r.data as any)?.url) { window.location.href = (r.data as any).url; return; }
      setError(`Checkout: ${(r.data as any)?.error || r.text || `HTTP ${r.status}`}. Use Stripe Portal in the meantime.`);
    } finally { setBusy(""); }
  }

  useEffect(() => { refreshAll(); }, []);

  const available = credits?.availableCbt ?? 0;
  const monthly = credits?.monthlyCbtRemaining ?? 0;
  const purchased = credits?.purchasedCbtRemaining ?? 0;

  const billingStatus = useMemo(() => { const s = (me?.subscription_status || "").toLowerCase(); return (s.includes("active") || s.includes("trial")) ? "ok" : "warn"; }, [me?.subscription_status]);
  const renewLabel = useMemo(() => { const s = (me?.subscription_status || "").toLowerCase(); if (s.includes("active") || s.includes("trial")) { const d = fmtDate(me?.current_period_end); return d !== "—" ? `Renews ${d}` : "Active"; } return me?.subscription_status || "—"; }, [me]);

  return (
    <AuthGate redirectTo={`${BASE}/login`} allowCookieSessionFallback>
      <div style={st.page}>
        <div style={st.wrap}>
          <div style={st.header}>
            <div>
              <div style={st.pills}><Pill tone={billingStatus as any}>{billingStatus === "ok" ? "Active" : "Attention"}</Pill><Pill>Credits</Pill></div>
              <h1 style={st.h1}>Buy Credits</h1>
              <div style={st.sub}>Top up your balance. Pricing shown at checkout.</div>
            </div>
            <div style={st.btnGroup}>
              <a href={`${BASE}/account`} style={st.btnGhost}>← Billing</a>
              <button type="button" style={st.btnGhost} onClick={refreshAll} disabled={busy !== ""}>Refresh</button>
              <button type="button" style={st.btnPrimary} onClick={openPortal} disabled={busy === "portal"}>{busy === "portal" ? "Opening..." : "Stripe Portal"}</button>
            </div>
          </div>

          {error ? <div style={st.errBox}>{error}</div> : null}

          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <div style={st.miniLabel}>Current Balance</div>
                  <div style={{ fontSize: 36, fontWeight: 700, color: "white", lineHeight: 1.1 }}>{loaded ? fmt(available) : "—"}</div>
                  <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginTop: 8 }}>{loaded ? <>{fmt(monthly)} monthly &bull; {fmt(purchased)} purchased</> : "Loading..."}</div>
                </div>
                <div style={st.miniStat}>
                  <div style={st.miniLabel}>Plan</div>
                  <div style={st.miniVal}>{me?.plan || "CodeBot"}</div>
                  <div style={st.miniSub}>{renewLabel}</div>
                </div>
              </div>
            </div>
          </div>

          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={st.sectionTitle}>Purchase Credits</div>
              <div style={st.sectionSub}>Select a tier below. Pricing is shown at Stripe checkout.</div>

              <div style={st.grid3}>
                {CREDIT_TIERS.map((tier) => (
                  <div key={tier.credits} style={st.tierCard(tier.tag === "Best Value")}>
                    {tier.tag ? <div style={st.tierTag}><Pill tone={tier.tag === "Best Value" ? "ok" : undefined}>{tier.tag}</Pill></div> : null}
                    <div style={{ fontSize: 32, fontWeight: 700, color: "white" }}>{fmt(tier.credits)}</div>
                    <div style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", marginTop: -8 }}>credits</div>
                    <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
                      <div style={st.dotRow}><div style={st.dot} /><span>Added instantly</span></div>
                      <div style={st.dotRow}><div style={st.dot} /><span>Never expires</span></div>
                      <div style={st.dotRow}><div style={st.dot} /><span>Stacks with monthly credits</span></div>
                    </div>
                    <button type="button" style={{ ...st.btnPrimary, width: "100%", justifyContent: "center", marginTop: 4 }} onClick={() => buyCredits(tier)} disabled={busy === `buy-${tier.credits}`}>
                      {busy === `buy-${tier.credits}` ? "Processing..." : `Buy ${fmt(tier.credits)} credits`}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={st.card}>
            <div style={st.cardBody}>
              <div style={st.sectionTitle}>How It Works</div>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {["Credits are consumed per build based on complexity", "Your plan includes monthly credits that reset each cycle", "Purchased credits stack on top and never expire", "Manage your subscription through the Stripe Portal"].map((b) => (
                  <div key={b} style={st.dotRow}><div style={st.dot} /><span>{b}</span></div>
                ))}
              </div>
            </div>
          </div>
          <div style={{ height: 20 }} />
        </div>
      </div>
    </AuthGate>
  );
}
