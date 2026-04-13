"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";

async function readText(res: Response): Promise<string> {
  return await res.text().catch(() => "");
}

async function apiJson<T>(
  path: string,
  init?: RequestInit
): Promise<{ ok: boolean; status: number; data?: T; text?: string }> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = (await res.json().catch(() => undefined)) as T | undefined;
    return { ok: res.ok, status: res.status, data };
  }
  return { ok: res.ok, status: res.status, text: await readText(res) };
}

type PortalOut = { url: string };

type CreditsOut = {
  availableCbt: number;
  monthlyCbtRemaining?: number;
  purchasedCbtRemaining?: number;
};

type MeOut = {
  id: string;
  email: string;
  is_admin: boolean;
  subscription_status?: string;
  plan?: string;
  current_period_end?: number; // unix seconds
  credits_remaining?: number | null;
  display_name?: string | null;
};

const PLAN = {
  key: "codebot",
  name: "CodeBot",
  price: "$50",
  cadence: "/month",
  desc: "Everything you need to build. Simple, consistent, high-usage.",
  bullets: [
    "≈ 4,000 monthly credits (≈ 4,000 prompts)",
    "Designed for daily building (don’t hoard credits)",
    "Stripe portal + cookie-session auth",
  ],
} as const;

// Keep packs, but visually demote + smaller copy
const PACKS = [
  { key: "pack20", name: "CBT Pack 20", price: "$20", desc: "One-time top-up", bullets: ["+20 purchased credits", "Does not expire"] },
  { key: "pack60", name: "CBT Pack 60", price: "$60", desc: "One-time top-up", bullets: ["+60 purchased credits", "Does not expire"] },
] as const;

function Pill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: "ok" | "warn" | "bad" | "brand" | "neutral";
}) {
  const cls =
    tone === "ok"
      ? "cb-pill2 ok"
      : tone === "warn"
      ? "cb-pill2 warn"
      : tone === "bad"
      ? "cb-pill2 bad"
      : tone === "brand"
      ? "cb-pill2 brand"
      : tone === "neutral"
      ? "cb-pill2"
      : "cb-pill2";
  return <span className={cls}>{children}</span>;
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <div className="cb-bullet">
      <span className="cb-bullet__check">✓</span>
      <span>{children}</span>
    </div>
  );
}

function formatDateFromUnixSeconds(sec?: number): string {
  if (!sec || !Number.isFinite(sec)) return "—";
  try {
    const d = new Date(sec * 1000);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
  } catch {
    return "—";
  }
}

export default function UpgradePage() {
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [credits, setCredits] = useState<CreditsOut | null>(null);
  const [me, setMe] = useState<MeOut | null>(null);

  const creditsLabel = useMemo(() => {
    if (!credits) return "—";
    const a = credits.availableCbt ?? 0;
    const m = credits.monthlyCbtRemaining;
    const p = credits.purchasedCbtRemaining;
    return `${a.toLocaleString()} available • ${String(m ?? "—")} monthly • ${String(p ?? "—")} purchased`;
  }, [credits]);

  const promptsLabel = useMemo(() => {
    if (!credits) return "—";
    const a = credits.availableCbt ?? 0;
    return `${a.toLocaleString()} prompts remaining`;
  }, [credits]);

  const billingCycleLabel = useMemo(() => {
    const status = (me?.subscription_status || "").toLowerCase().trim();
    const end = me?.current_period_end;

    if (!status) return "—";
    if (status.includes("active") || status.includes("trial")) {
      const renew = formatDateFromUnixSeconds(end);
      return renew !== "—" ? `Renews on ${renew}` : "Active (renewal date unavailable)";
    }
    if (status.includes("past_due")) return "Past due";
    if (status.includes("incomplete")) return "Incomplete";
    if (status.includes("canceled") || status.includes("cancelled")) return "Canceled";
    return me?.subscription_status || "—";
  }, [me?.subscription_status, me?.current_period_end]);

  const billingPillTone = useMemo<"ok" | "warn" | "bad">(() => {
    const s = (me?.subscription_status || "").toLowerCase();
    if (!s) return "warn";
    if (s.includes("active") || s.includes("trial")) return "ok";
    if (s.includes("past_due") || s.includes("incomplete")) return "warn";
    return "bad";
  }, [me?.subscription_status]);

  async function loadCredits() {
    setError("");
    const res = await apiJson<CreditsOut>("/api/credits/balance");
    if (res.ok && res.data) setCredits(res.data);
  }

  async function loadMe() {
    // Prefer whoami, fallback to /api/profile (matches Settings)
    const who = await apiJson<MeOut>("/api/auth/whoami");
    if (who.ok && who.data) {
      setMe(who.data);
      return;
    }
    const prof = await apiJson<MeOut>("/api/profile");
    if (prof.ok && prof.data) {
      setMe(prof.data);
      return;
    }
    setMe(null);
  }

  async function refreshAll() {
    await Promise.all([loadMe(), loadCredits()]);
  }

  async function openBillingPortal() {
    setError("");
    setBusy("portal");
    try {
      const res = await apiJson<PortalOut>("/api/billing/portal");
      if (!res.ok || !res.data?.url) {
        setError(`Billing portal failed (HTTP ${res.status}).`);
        return;
      }
      window.location.href = res.data.url;
    } finally {
      setBusy("");
    }
  }

  // We keep buttons disabled until checkout routes exist.
  function notWired(kind: "plan" | "pack") {
    setError(
      kind === "plan"
        ? "Checkout is not wired yet. Stripe portal + credits are live. Next: wire the subscription checkout session route."
        : "Pack checkout is not wired yet. Stripe portal + credits are live. Next: wire the pack checkout session route."
    );
  }

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthGate redirectTo={`${BASE}/login`} allowCookieSessionFallback={true}>
      <div className="cb-pricing-wrap cb-bg">
        <div className="mx-auto w-full max-w-6xl">
          {/* HERO */}
          <div className="cb-upgrade-hero">
            <div className="cb-upgrade-hero__left">
              <div className="cb-upgrade-hero__kicker">
                <Pill tone="brand">CodeBot Billing</Pill>
                <span className="cb-muted">Use credits aggressively — they’re meant to be spent.</span>
              </div>

              <div className="cb-upgrade-hero__title">Billing & Credits</div>
              <div className="cb-upgrade-hero__sub">
                Simple plan structure. Clear cycle info. Credits are designed to be used — not saved.
              </div>

              <div className="cb-actions" style={{ marginTop: 12 }}>
                <Link href={`${BASE}/account`} className="no-underline">
                  <button className="cb-btn">← Back to Account</button>
                </Link>
                <button className="cb-btn" onClick={refreshAll}>
                  Refresh
                </button>
                <button className="cb-btn primary" onClick={openBillingPortal} disabled={busy === "portal"}>
                  {busy === "portal" ? "Opening…" : "Open Stripe Portal"}
                </button>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="cb-kpi">
                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label">Credits</div>
                    <div className="cb-kpi__value">{credits ? creditsLabel : "Loading…"}</div>
                    <div className="cb-kpi__sub">{credits ? promptsLabel : ""}</div>
                  </div>

                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      Billing cycle <Pill tone={billingPillTone}>{(me?.subscription_status || "—").toString()}</Pill>
                    </div>
                    <div className="cb-kpi__value">{billingCycleLabel}</div>
                    <div className="cb-kpi__sub">
                      {me?.plan ? `Plan: ${me.plan}` : "Plan: —"}
                    </div>
                  </div>
                </div>
              </div>

              <div className="cb-note" style={{ marginTop: 12 }}>
                <b>Behavior goal:</b> make users comfortable spending credits. The UI intentionally emphasizes usage and velocity.
              </div>
            </div>

            <div className="cb-upgrade-hero__right">
              <div className="cb-card">
                <div className="cb-card__head">
                  <div>
                    <div className="cb-card__title">What’s live right now</div>
                    <div className="cb-card__sub">Portal + credits confirmed working</div>
                  </div>
                  <Pill tone="ok">LIVE</Pill>
                </div>
                <div className="cb-card__body">
                  <div className="cb-featurelist">
                    <div className="cb-feature">
                      <div className="cb-feature__dot" />
                      <div>
                        <div className="cb-feature__title">Stripe customer portal</div>
                        <div className="cb-feature__desc">GET /api/billing/portal → returns URL</div>
                      </div>
                    </div>
                    <div className="cb-feature">
                      <div className="cb-feature__dot" />
                      <div>
                        <div className="cb-feature__title">Credits balance</div>
                        <div className="cb-feature__desc">GET /api/credits/balance → returns credit breakdown</div>
                      </div>
                    </div>
                    <div className="cb-feature">
                      <div className="cb-feature__dot" />
                      <div>
                        <div className="cb-feature__title">Session auth</div>
                        <div className="cb-feature__desc">Cookie path=/codebot, SameSite=Lax</div>
                      </div>
                    </div>
                  </div>

                  <div className="cb-divider" />

                  <div className="cb-note">
                    Next: wire the exact Stripe checkout session routes for subscriptions + packs. Until then, we don’t pretend buttons are live.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ERROR */}
          {error ? (
            <div className="cb-note" style={{ borderColor: "rgba(239,68,68,0.25)", background: "rgba(239,68,68,0.10)", marginTop: 12 }}>
              {error}
            </div>
          ) : null}

          {/* PLAN (SINGLE) */}
          <div className="cb-upgrade-section">
            <div className="cb-upgrade-section__head">
              <div>
                <div className="cb-upgrade-h2">Plan</div>
                <div className="cb-muted">One plan. No noise.</div>
              </div>
            </div>

            <div className="cb-upgrade-grid">
              <div className="cb-pricing cb-pricing--featured">
                <div>
                  <div className="cb-pricing__name">
                    <span>{PLAN.name}</span>
                    <Pill tone="brand">Recommended</Pill>
                  </div>

                  <div className="cb-pricing__price">
                    <span className="cb-pricing__priceBig">{PLAN.price}</span>
                    <span className="cb-pricing__cadence">{PLAN.cadence}</span>
                  </div>

                  <div className="cb-pricing__tagline">{PLAN.desc}</div>
                </div>

                <div className="cb-pricing__bullets">
                  {PLAN.bullets.map((b) => (
                    <Bullet key={b}>{b}</Bullet>
                  ))}
                </div>

                <div className="cb-pricing__actions">
                  <button className="cb-btn primary" onClick={() => notWired("plan")}>
                    Upgrade
                  </button>
                  <button className="cb-btn" onClick={openBillingPortal}>
                    Manage
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* PACKS (DEMOTED) */}
          <div className="cb-upgrade-section">
            <div className="cb-upgrade-section__head">
              <div>
                <div className="cb-upgrade-h2">Top-up packs</div>
                <div className="cb-muted">Optional. De-emphasized by design.</div>
              </div>
            </div>

            <details className="cb-packs-details">
              <summary className="cb-packs-summary">
                <span>Show CBT Packs</span>
                <span className="cb-muted">(one-time)</span>
              </summary>

              <div className="cb-upgrade-grid cb-upgrade-grid--packs">
                {PACKS.map((p) => (
                  <div key={p.key} className="cb-pricing cb-pricing--pack">
                    <div>
                      <div className="cb-pricing__name">{p.name}</div>
                      <div className="cb-pricing__price">
                        <span className="cb-pricing__priceBig">{p.price}</span>
                        <span className="cb-pricing__cadence">one-time</span>
                      </div>
                      <div className="cb-pricing__tagline">{p.desc}</div>
                    </div>

                    <div className="cb-pricing__bullets">
                      {p.bullets.map((b) => (
                        <Bullet key={b}>{b}</Bullet>
                      ))}
                    </div>

                    <div className="cb-pricing__actions">
                      <button className="cb-btn primary" onClick={() => notWired("pack")}>
                        Buy pack
                      </button>
                      <button className="cb-btn" onClick={loadCredits}>
                        Refresh
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </div>

          <div style={{ height: 24 }} />
        </div>
      </div>
    </AuthGate>
  );
}
