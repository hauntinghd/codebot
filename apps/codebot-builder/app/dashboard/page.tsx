"use client";

import React, {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
} from "react";
import Link from "next/link";
import AuthGate from "@/components/AuthGate";

const BASE = "/codebot";

type WhoAmI = {
  authenticated: boolean;
  id?: string;
  email?: string;
  is_admin?: boolean;
};

async function apiJson<T>(
  path: string
): Promise<{ ok: boolean; status: number; data?: T }> {
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
  const bg =
    tone === "ok"
      ? "rgba(34,197,94,0.12)"
      : tone === "warn"
      ? "rgba(245,158,11,0.12)"
      : "rgba(255,255,255,0.06)";
  const color =
    tone === "ok"
      ? "rgba(134,239,172,1)"
      : tone === "warn"
      ? "rgba(253,224,71,1)"
      : "rgba(255,255,255,0.6)";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        borderRadius: "6px",
        padding: "4px 10px",
        fontSize: "11px",
        fontWeight: 500,
        letterSpacing: "0.025em",
        whiteSpace: "nowrap",
        background: bg,
        color: color,
      }}
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
        <div className="min-w-0">
          <div className="cb-card__title">{props.title}</div>
          {props.subtitle ? (
            <div className="cb-card__sub">{props.subtitle}</div>
          ) : null}
        </div>
        {props.right ? <div className="shrink-0">{props.right}</div> : null}
      </div>
      <div className="cb-card__body">{props.children}</div>
    </div>
  );
}

function initials(email?: string) {
  if (!email) return "U";
  const left = email.split("@")[0] || "";
  const parts = left.split(/[._-]+/).filter(Boolean);
  const a = (parts[0]?.[0] || left[0] || "U").toUpperCase();
  const b = (parts[1]?.[0] || left[1] || "").toUpperCase();
  return (a + b).trim() || "U";
}

/**
 * Close dropdown when clicking outside OR pressing Escape.
 * Uses refs that can be null without TypeScript fighting you.
 */
function useOutsideClose(
  open: boolean,
  refs: Array<React.RefObject<HTMLElement | null>>,
  onClose: () => void
) {
  useEffect(() => {
    if (!open) return;

    const onDown = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (!t) return;

      for (const r of refs) {
        const el = r.current;
        if (el && el.contains(t)) return;
      }
      onClose();
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    window.addEventListener("mousedown", onDown, { capture: true });
    window.addEventListener("keydown", onKey);

    return () => {
      window.removeEventListener("mousedown", onDown, { capture: true } as any);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, refs, onClose]);
}

type MenuPos = { left: number; top: number; width: number };

export default function DashboardPage() {
  const [me, setMe] = useState<WhoAmI | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // profile menu
  const [menuOpen, setMenuOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // fixed-position menu coordinates (prevents right-edge clipping)
  const [menuPos, setMenuPos] = useState<MenuPos>({
    left: 0,
    top: 0,
    width: 260,
  });

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

  const email = me?.email || "";
  const isAdmin = !!me?.is_admin;

  const load = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const logout = useCallback(async () => {
    try {
      await fetch(`${BASE}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore
    }
    window.location.assign("/codebot/login");
  }, []);

  useOutsideClose(menuOpen, [btnRef, menuRef], () => setMenuOpen(false));

  /**
   * Compute a fixed-position dropdown that:
   * - centers under the profile button
   * - clamps inside viewport so it never clips
   * - updates on open, resize, scroll
   */
  const computeMenuPos = useCallback(() => {
    const btn = btnRef.current;
    if (!btn) return;

    const r = btn.getBoundingClientRect();
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;

    const margin = 12;
    const width = 260;

    // Desired: centered under button
    let left = r.left + r.width / 2 - width / 2;

    // Clamp so it never clips
    left = Math.max(margin, Math.min(left, viewportW - margin - width));

    // Drop below button; if near bottom, still clamp (simple)
    let top = r.bottom + 10;
    top = Math.max(margin, Math.min(top, viewportH - margin - 260)); // 260 ~ menu height guard

    setMenuPos({ left, top, width });
  }, []);

  useLayoutEffect(() => {
    if (!menuOpen) return;
    computeMenuPos();

    const onResize = () => computeMenuPos();
    const onScroll = () => computeMenuPos();

    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onScroll, true);

    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [menuOpen, computeMenuPos]);

  return (
    <AuthGate redirectTo="/login" allowCookieSessionFallback={true}>
      <div className="cb-settings cb-bg cb-dashboard">
        <div className="relative z-10 mx-auto w-full max-w-6xl">
          {/* Header */}
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: "32px", marginBottom: "48px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "8px",
                    borderRadius: "6px",
                    padding: "5px 12px",
                    fontSize: "12px",
                    fontWeight: 500,
                    background: statusTone === "ok" ? "rgba(34,197,94,0.12)" : statusTone === "warn" ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.06)",
                    color: statusTone === "ok" ? "rgba(134,239,172,1)" : statusTone === "warn" ? "rgba(253,224,71,1)" : "rgba(255,255,255,0.6)",
                  }}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "currentColor", opacity: 0.8 }} />
                  {statusText}
                </span>
                <Tag>Cookie session • /codebot</Tag>
                {isAdmin ? <Tag>Admin</Tag> : null}
              </div>

              <div>
                <h1 style={{ fontSize: "32px", fontWeight: 600, color: "white", letterSpacing: "-0.02em", margin: 0 }}>
                  Dashboard
                </h1>
                <p style={{ marginTop: "8px", fontSize: "15px", color: "rgba(255,255,255,0.5)", lineHeight: 1.6 }}>
                  Launch builds, manage billing, and update your account.
                </p>
              </div>
            </div>

            {/* Top-right actions */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <button
                type="button"
                onClick={load}
                style={{ height: "40px", padding: "0 16px", borderRadius: "10px", border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", fontSize: "14px", fontWeight: 500, cursor: "pointer" }}
              >
                Refresh
              </button>

              <Link href="/builder" style={{ textDecoration: "none" }}>
                <button
                  type="button"
                  style={{ height: "40px", padding: "0 20px", borderRadius: "10px", border: "none", background: "white", color: "#0b0f14", fontSize: "14px", fontWeight: 600, cursor: "pointer" }}
                >
                  Open Builder
                </button>
              </Link>

              <button
                ref={btnRef}
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                style={{ height: "40px", padding: "0 12px", borderRadius: "10px", border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", fontSize: "14px", fontWeight: 500, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "8px" }}
              >
                <span style={{ display: "inline-flex", width: "28px", height: "28px", alignItems: "center", justifyContent: "center", borderRadius: "50%", background: "rgba(255,255,255,0.08)", fontSize: "12px", fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
                  {initials(email)}
                </span>
                <span style={{ fontSize: "14px", color: "rgba(255,255,255,0.6)" }}>▾</span>
              </button>
            </div>
          </div>

          {/* Dropdown (fixed-position; cannot clip) */}
          {menuOpen ? (
            <div
              ref={menuRef}
              role="menu"
              style={{
                position: "fixed",
                zIndex: 1000,
                borderRadius: "12px",
                background: "rgba(15,20,25,0.98)",
                backdropFilter: "blur(20px)",
                boxShadow: "0 24px 48px -12px rgba(0,0,0,0.6)",
                overflow: "hidden",
                left: menuPos.left,
                top: menuPos.top,
                width: menuPos.width,
              }}
            >
              <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.05em", color: "rgba(255,255,255,0.45)" }}>
                  SIGNED IN
                </div>
                <div style={{ marginTop: "4px", fontSize: "14px", fontWeight: 600, color: "white" }}>
                  {email || "—"}
                </div>
                <div style={{ marginTop: "4px", fontSize: "11px", color: "rgba(255,255,255,0.4)" }}>
                  {isAdmin ? `Admin • ${me?.id || ""}` : me?.id || ""}
                </div>
              </div>

              <div style={{ padding: "8px" }}>
                {[
                  { href: "/account", label: "Account" },
                  { href: "/settings", label: "Settings" },
                  { href: "/account/upgrade", label: "Upgrade / Billing" },
                  { href: "/terms", label: "Terms" },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    style={{ textDecoration: "none", display: "block" }}
                    onClick={() => setMenuOpen(false)}
                  >
                    <div style={{ borderRadius: "8px", padding: "10px 12px", fontSize: "14px", fontWeight: 500, color: "rgba(255,255,255,0.8)" }}>
                      {item.label}
                    </div>
                  </Link>
                ))}
              </div>

              <div style={{ padding: "8px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                <button
                  type="button"
                  onClick={logout}
                  style={{ width: "100%", height: "40px", borderRadius: "10px", border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", fontSize: "14px", fontWeight: 500, cursor: "pointer" }}
                >
                  Sign out
                </button>
              </div>
            </div>
          ) : null}

          {err ? (
            <div className="mb-6 whitespace-pre-wrap rounded-xl bg-red-500/10 p-4 text-sm text-red-200">
              {err}
            </div>
          ) : null}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            {/* Account Status */}
            <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: "16px", padding: "40px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
                <div>
                  <h2 style={{ fontSize: "18px", fontWeight: 600, color: "white", margin: 0 }}>Account Status</h2>
                  <p style={{ fontSize: "14px", color: "rgba(255,255,255,0.45)", marginTop: "4px" }}>Current session and access level</p>
                </div>
                <Tag tone={statusTone}>{statusText}</Tag>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <svg width="24" height="24" fill="none" stroke="rgba(255,255,255,0.6)" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: "11px", fontWeight: 500, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "4px" }}>Role</div>
                  <div style={{ fontSize: "22px", fontWeight: 600, color: "white" }}>
                    {loading ? "—" : me?.is_admin ? "Administrator" : "User"}
                  </div>
                  <div style={{ fontSize: "14px", color: "rgba(255,255,255,0.45)", marginTop: "4px" }}>Full access to build and deploy</div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: "16px", padding: "40px" }}>
              <div style={{ marginBottom: "24px" }}>
                <h2 style={{ fontSize: "18px", fontWeight: 600, color: "white", margin: 0 }}>Quick Actions</h2>
                <p style={{ fontSize: "14px", color: "rgba(255,255,255,0.45)", marginTop: "4px" }}>Access key features</p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <Link href="/builder" className="no-underline block">
                  <div style={{ padding: "14px 16px", borderRadius: "10px", background: "rgba(255,255,255,0.07)", color: "white", fontSize: "15px", fontWeight: 600, cursor: "pointer" }}>
                    Build now
                  </div>
                </Link>
                <Link href="/account" className="no-underline block">
                  <div style={{ padding: "14px 16px", borderRadius: "10px", color: "rgba(255,255,255,0.85)", fontSize: "15px", fontWeight: 500, cursor: "pointer" }}>
                    Account
                  </div>
                </Link>
                <Link href="/settings" className="no-underline block">
                  <div style={{ padding: "14px 16px", borderRadius: "10px", color: "rgba(255,255,255,0.85)", fontSize: "15px", fontWeight: 500, cursor: "pointer" }}>
                    Settings
                  </div>
                </Link>
                <Link href="/account/upgrade" className="no-underline block">
                  <div style={{ padding: "14px 16px", borderRadius: "10px", color: "rgba(255,255,255,0.85)", fontSize: "15px", fontWeight: 500, cursor: "pointer" }}>
                    Upgrade / Billing
                  </div>
                </Link>
                <Link href="/terms" className="no-underline block">
                  <div style={{ padding: "14px 16px", borderRadius: "10px", color: "rgba(255,255,255,0.85)", fontSize: "15px", fontWeight: 500, cursor: "pointer" }}>
                    Terms
                  </div>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
