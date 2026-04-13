"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";

type WhoAmI = {
  authenticated: boolean;
  id?: string;
  email?: string;
  is_admin?: boolean;
};

async function apiJson<T>(path: string): Promise<{ ok: boolean; status: number; data?: T }> {
  const res = await fetch(`${BASE}${path}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
    headers: { accept: "application/json" },
  });

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return { ok: false, status: res.status };
  const data = (await res.json().catch(() => undefined)) as T | undefined;
  return { ok: res.ok, status: res.status, data };
}

function Tag({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "ok" | "warn";
}) {
  const cls =
    tone === "ok"
      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
      : tone === "warn"
        ? "border-amber-500/25 bg-amber-500/10 text-amber-200"
        : "border-white/10 bg-white/5 text-white/80";

  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-extrabold tracking-wide",
        cls,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

function Card(props: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="cb-card">
      <div className="cb-card__head">
        <div>
          <div className="cb-card__title">{props.title}</div>
          {props.subtitle ? <div className="cb-card__sub">{props.subtitle}</div> : null}
        </div>
        {props.right ? <div className="shrink-0">{props.right}</div> : null}
      </div>
      <div className="cb-card__body">{props.children}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [me, setMe] = useState<WhoAmI | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const statusTone = useMemo(() => {
    if (loading) return "neutral" as const;
    if (me?.authenticated) return "ok" as const;
    return "warn" as const;
  }, [loading, me]);

  const statusText = useMemo(() => {
    if (loading) return "Checking…";
    if (me?.authenticated) return "Authenticated";
    return "Not authenticated";
  }, [loading, me]);

  async function load() {
    setErr("");
    setLoading(true);
    const res = await apiJson<WhoAmI>("/api/auth/whoami");
    if (res.ok && res.data) {
      setMe(res.data);
      setLoading(false);
      return;
    }
    setMe(null);
    setLoading(false);
    setErr(`Failed to load whoami (HTTP ${res.status}).`);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <AuthGate redirectTo="/codebot/login" allowCookieSessionFallback={true}>
      <div className="cb-settings cb-bg">
        <div className="mx-auto w-full max-w-6xl">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <Tag tone={statusTone}>{statusText}</Tag>
                <Tag>Cookie session • /codebot</Tag>
              </div>
              <div className="text-[22px] font-black tracking-tight text-white">Dashboard</div>
              <div className="text-sm text-white/70">
                Launch builds, manage billing, and update your account.
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button className="cb-btn" type="button" onClick={load}>
                Refresh
              </button>
              <Link href="/codebot/builder" className="no-underline">
                <button className="cb-btn primary" type="button">
                  Open Builder
                </button>
              </Link>
            </div>
          </div>

          {err ? (
            <div className="mb-4 whitespace-pre-wrap rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-200">
              {err}
            </div>
          ) : null}

          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 lg:col-span-7">
              <Card
                title="Session"
                subtitle="Live auth state from /api/auth/whoami"
                right={<Tag tone={statusTone}>{statusText}</Tag>}
              >
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="text-xs font-extrabold text-white/70">Email</div>
                    <div className="mt-2 text-base font-black text-white">
                      {loading ? "—" : me?.email || "—"}
                    </div>
                  </div>

                  <div className="grid grid-cols-12 gap-3">
                    <div className="col-span-12 md:col-span-6 rounded-2xl border border-white/10 bg-black/20 p-4">
                      <div className="text-xs font-extrabold text-white/70">User ID</div>
                      <div className="mt-2 text-sm text-white/80 break-all">
                        {loading ? "—" : me?.id || "—"}
                      </div>
                    </div>

                    <div className="col-span-12 md:col-span-6 rounded-2xl border border-white/10 bg-black/20 p-4">
                      <div className="text-xs font-extrabold text-white/70">Role</div>
                      <div className="mt-2 text-sm text-white/80">
                        {loading ? "—" : me?.is_admin ? "Admin" : "User"}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            <div className="col-span-12 lg:col-span-5">
              <Card title="Quick actions" subtitle="Everything important in 1 click">
                <div className="grid gap-2">
                  <Link href="/codebot/builder" className="no-underline">
                    <button className="cb-btn primary w-full" type="button">
                      Build now
                    </button>
                  </Link>
                  <Link href="/codebot/account" className="no-underline">
                    <button className="cb-btn w-full" type="button">
                      Account
                    </button>
                  </Link>
                  <Link href="/codebot/settings" className="no-underline">
                    <button className="cb-btn w-full" type="button">
                      Settings
                    </button>
                  </Link>
                  <Link href="/codebot/account/upgrade" className="no-underline">
                    <button className="cb-btn w-full" type="button">
                      Upgrade / Billing
                    </button>
                  </Link>
                  <Link href="/codebot/terms" className="no-underline">
                    <button className="cb-btn w-full" type="button">
                      Terms
                    </button>
                  </Link>
                </div>

                <div className="mt-4 text-xs text-white/45">
                  This dashboard is intentionally minimal. It’s “ship-ready”, not “fancy and fragile”.
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
