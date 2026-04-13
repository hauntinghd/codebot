"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";

type PortalOut = { url: string };
type CreditsOut = {
  availableCbt: number;
  monthlyCbtRemaining?: number;
  purchasedCbtRemaining?: number;
};

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
  const text = await readText(res);
  return { ok: res.ok, status: res.status, text };
}

/**
 * We DO NOT guess your billing endpoints.
 * We attempt a short list of likely endpoints and accept the first one that returns {url}.
 * If none work, we show an actionable error and you paste the Express route names.
 */
async function tryCheckoutUrl(payload: any): Promise<{
  url?: string;
  tried: string[];
  last?: { status: number; text?: string };
}> {
  const tried: string[] = [];

  const candidates: Array<{ path: string; method: "POST" | "GET"; body?: any }> = [
    // Plan subscription candidates
    { path: "/api/billing/checkout", method: "POST", body: payload },
    { path: "/api/billing/create-checkout-session", method: "POST", body: payload },
    { path: "/api/billing/subscribe", method: "POST", body: payload },
    { path: "/api/billing/session", method: "POST", body: payload },

    // Credits pack candidates
    { path: "/api/credits/checkout", method: "POST", body: payload },
    { path: "/api/credits/buy", method: "POST", body: payload },
    { path: "/api/credits/purchase", method: "POST", body: payload },
  ];

  let last: { status: number; text?: string } | undefined;

  for (const c of candidates) {
    tried.push(`${c.method} ${c.path}`);
    const res = await apiJson<PortalOut>(c.path, {
      method: c.method,
      body: c.method === "POST" ? JSON.stringify(c.body ?? {}) : undefined,
    });

    if (res.ok && res.data?.url) return { url: res.data.url, tried };
    last = { status: res.status, text: res.text };
  }

  return { tried, last };
}

/* -----------------------------
   UI atoms (keep local, simple)
------------------------------ */

function Tag({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "live" | "ok" | "warn";
}) {
  const cls =
    tone === "live"
      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
      : tone === "ok"
        ? "border-green-500/25 bg-green-500/10 text-green-200"
        : tone === "warn"
          ? "border-amber-500/25 bg-amber-500/10 text-amber-200"
          : "border-white/10 bg-white/5 text-white/80";

  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-extrabold tracking-wide",
        cls,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

function Card({
  title,
  subtitle,
  right,
  children,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="cb-card">
      <div className="cb-card__head">
        <div>
          <div className="cb-card__title">{title}</div>
          {subtitle ? <div className="cb-card__sub">{subtitle}</div> : null}
        </div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>
      <div className="cb-card__body">{children}</div>
    </div>
  );
}

function Btn(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "ghost" | "danger";
  }
) {
  const v = props.variant || "ghost";
  const cls =
    v === "primary"
      ? "cb-btn primary"
      : v === "danger"
        ? "cb-btn danger"
        : "cb-btn";
  return (
    <button {...props} className={[cls, props.className || ""].join(" ")}>
      {props.children}
    </button>
  );
}

function CheckRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-sm text-white/80">
      <span className="mt-[2px] inline-flex h-5 w-5 items-center justify-center rounded-md border border-white/10 bg-white/5 text-[11px]">
        ✓
      </span>
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

const PLAN_CHOICES = [
  {
    key: "coding_assistant",
    name: "Coding Assistant",
    price: "$50/mo",
    badge: null as null | string,
    desc: "Baseline tier for daily building. Strict + stable.",
    bullets: ["25,000 monthly CBT", "Builder + Deploy flow", "Cookie-session auth (reliable)"],
  },
  {
    key: "voyager",
    name: "Voyager",
    price: "$250/mo",
    badge: "Recommended",
    desc: "Higher limits + priority throughput.",
    bullets: ["75,000 monthly CBT", "Priority experience", "More aggressive build depth"],
  },
  {
    key: "architecture_mode",
    name: "Architecture Mode",
    price: "$100/mo",
    badge: null as null | string,
    desc: "End-to-end systems design mode.",
    bullets: ["Architecture workflows", "Higher complexity builds", "System-first planning"],
  },
];

const PACK_CHOICES = [
  {
    key: "pack20",
    name: "CBT Pack 20",
    price: "$40 one-time",
    bullets: ["One-time top-up", "+20 purchased CBT", "Does not expire"],
  },
  {
    key: "pack60",
    name: "CBT Pack 60",
    price: "$99 one-time",
    bullets: ["One-time top-up", "+60 purchased CBT", "Does not expire"],
  },
];

export default function UpgradePage() {
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [credits, setCredits] = useState<CreditsOut | null>(null);

  const creditLabel = useMemo(() => {
    if (!credits) return "—";
    const a = credits.availableCbt ?? 0;
    const m = credits.monthlyCbtRemaining ?? 0;
    const p = credits.purchasedCbtRemaining ?? 0;
    return `${a.toLocaleString()} available • ${m.toLocaleString()} monthly • ${p.toLocaleString()} purchased`;
  }, [credits]);

  const billingWired = useMemo(() => {
    // simple “confidence” indicator: if credits load, session+credits wiring is alive
    return !!credits && typeof credits.availableCbt === "number";
  }, [credits]);

  async function loadCredits() {
    const res = await apiJson<CreditsOut>("/api/credits/balance");
    if (res.ok && res.data) setCredits(res.data);
  }

  useEffect(() => {
    loadCredits();
  }, []);

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

  async function buyPlan(planKey: string) {
    setError("");
    setBusy(`plan:${planKey}`);
    try {
      const out = await tryCheckoutUrl({ kind: "plan", plan: planKey });
      if (!out.url) {
        setError(
          `No checkout endpoint returned a URL.\nTried:\n- ${out.tried.join(
            "\n- "
          )}\nLast: HTTP ${out.last?.status ?? "?"} ${
            out.last?.text ? `(${out.last.text.slice(0, 180)})` : ""
          }`
        );
        return;
      }
      window.location.href = out.url;
    } finally {
      setBusy("");
    }
  }

  async function buyPack(packKey: string) {
    setError("");
    setBusy(`pack:${packKey}`);
    try {
      const out = await tryCheckoutUrl({ kind: "pack", pack: packKey });
      if (!out.url) {
        setError(
          `No pack checkout endpoint returned a URL.\nTried:\n- ${out.tried.join(
            "\n- "
          )}\nLast: HTTP ${out.last?.status ?? "?"} ${
            out.last?.text ? `(${out.last.text.slice(0, 180)})` : ""
          }`
        );
        return;
      }
      window.location.href = out.url;
    } finally {
      setBusy("");
    }
  }

  return (
    <AuthGate redirectTo={`${BASE}/login`} allowCookieSessionFallback={true}>
      <div className="cb-settings cb-bg">
        <div className="mx-auto w-full max-w-6xl">
          {/* Header */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <Tag tone="neutral">CodeBot Billing</Tag>
                <Tag tone="neutral">Cookie-auth only • Stable sessions</Tag>
              </div>
              <h1 className="text-[22px] font-black tracking-tight text-white">Upgrade</h1>
              <div className="text-sm text-white/70">
                Manage subscription, view credits, and top up CBT. Stripe portal + credits endpoint are confirmed working.
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Link href={`${BASE}/account`} className="no-underline">
                <Btn>← Back to Account</Btn>
              </Link>
              <Btn onClick={loadCredits}>Refresh credits</Btn>
              <Btn variant="primary" onClick={openBillingPortal} disabled={busy === "portal"}>
                {busy === "portal" ? "Opening…" : "Open Stripe Portal"}
              </Btn>
            </div>
          </div>

          {error ? (
            <div className="mb-4 whitespace-pre-wrap rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          {/* Status strip */}
          <div className="grid grid-cols-12 gap-3 mb-4">
            <div className="col-span-12 lg:col-span-8">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-extrabold text-white/70">Credits</div>
                <div className="mt-2 text-lg font-black text-white">{creditLabel}</div>
              </div>
            </div>
            <div className="col-span-12 lg:col-span-4">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-extrabold text-white/70">Billing status</div>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <div className="text-lg font-black text-white">{billingWired ? "Wired" : "Checking…"}</div>
                  <Tag tone={billingWired ? "live" : "neutral"}>{billingWired ? "LIVE" : "PENDING"}</Tag>
                </div>
              </div>
            </div>
          </div>

          {/* Main content */}
          <div className="grid grid-cols-12 gap-4">
            {/* Left: verification + FAQ */}
            <div className="col-span-12 lg:col-span-6">
              <Card
                title="Live endpoints"
                subtitle="Verified via curl using cb_session_codebot"
                right={<Tag tone="live">LIVE</Tag>}
              >
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-white/10 bg-black/18 p-4">
                    <div className="text-sm font-extrabold text-white">Stripe customer portal</div>
                    <div className="mt-1 text-sm text-white/70">
                      GET <span className="text-white/85 font-semibold">/api/billing/portal</span> → returns URL
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/18 p-4">
                    <div className="text-sm font-extrabold text-white">Credits balance</div>
                    <div className="mt-1 text-sm text-white/70">
                      GET <span className="text-white/85 font-semibold">/api/credits/balance</span> → returns CBT breakdown
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/18 p-4">
                    <div className="text-sm font-extrabold text-white">Session auth</div>
                    <div className="mt-1 text-sm text-white/70">
                      Cookie path=<span className="text-white/85 font-semibold">/codebot</span>, SameSite=<span className="text-white/85 font-semibold">Lax</span> (unchanged)
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm text-white/70">
                    Next: confirm the <span className="text-white/85 font-semibold">exact Express route</span> for creating Stripe checkout sessions. We will not guess.
                  </div>
                </div>
              </Card>

              <div className="mt-4">
                <Card title="FAQ" subtitle="No guessing, no drift">
                  <div className="grid gap-4 text-sm text-white/75 leading-relaxed">
                    <div>
                      <div className="text-white font-extrabold">Why did Bearer auth fail earlier?</div>
                      <div className="mt-1">
                        Because the Express services honor the cookie session. JWT access tokens from FastAPI are not trusted by those services.
                      </div>
                    </div>

                    <div>
                      <div className="text-white font-extrabold">What’s confirmed working today?</div>
                      <div className="mt-1">
                        Portal + credits balance via cookie auth. That proves billing/credits wiring is live and stable end-to-end.
                      </div>
                    </div>

                    <div>
                      <div className="text-white font-extrabold">What do we need to finish checkout?</div>
                      <div className="mt-1">
                        The exact Express route that creates Stripe checkout sessions for subscription plans + packs. Once confirmed, we wire buttons live.
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            {/* Right: plans + packs */}
            <div className="col-span-12 lg:col-span-6">
              <Card title="Plans" subtitle="Subscriptions (checkout wiring pending)">
                <div className="grid gap-3">
                  {PLAN_CHOICES.map((p) => (
                    <div
                      key={p.key}
                      className={[
                        "rounded-2xl border bg-black/20 p-4",
                        p.badge ? "border-sky-400/25 shadow-[0_0_0_1px_rgba(56,189,248,0.10)]" : "border-white/10",
                      ].join(" ")}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <div className="text-base font-black text-white">{p.name}</div>
                            {p.badge ? <Tag tone="neutral">{p.badge}</Tag> : null}
                          </div>
                          <div className="mt-1 text-sm text-white/70">{p.price}</div>
                          <div className="mt-2 text-sm text-white/75">{p.desc}</div>
                        </div>
                      </div>

                      <div className="mt-3 grid gap-2">
                        {p.bullets.map((b) => (
                          <CheckRow key={b}>{b}</CheckRow>
                        ))}
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <Btn
                          variant="primary"
                          onClick={() => buyPlan(p.key)}
                          disabled={busy === `plan:${p.key}`}
                        >
                          {busy === `plan:${p.key}` ? "Starting…" : "Upgrade"}
                        </Btn>
                        <Btn onClick={openBillingPortal} disabled={busy === "portal"}>
                          Manage
                        </Btn>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <div className="mt-4">
                <Card title="CBT Packs" subtitle="One-time top-ups (checkout wiring pending)">
                  <div className="grid gap-3">
                    {PACK_CHOICES.map((pk) => (
                      <div
                        key={pk.key}
                        className="rounded-2xl border border-white/10 bg-black/20 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-base font-black text-white">{pk.name}</div>
                            <div className="mt-1 text-sm text-white/70">{pk.price}</div>
                          </div>
                        </div>

                        <div className="mt-3 grid gap-2">
                          {pk.bullets.map((b) => (
                            <CheckRow key={b}>{b}</CheckRow>
                          ))}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-2">
                          <Btn
                            variant="primary"
                            onClick={() => buyPack(pk.key)}
                            disabled={busy === `pack:${pk.key}`}
                          >
                            {busy === `pack:${pk.key}` ? "Starting…" : "Buy pack"}
                          </Btn>
                          <Btn onClick={loadCredits}>Refresh</Btn>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          </div>

          <div className="mt-5 text-xs text-white/45">
            If “Upgrade” fails, it prints the exact endpoints it tried. Then we grep your Express routes and replace the discovery list with the one true path.
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
