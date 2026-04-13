"use client";
import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type MeOut = {
  id: string;
  email: string;
  is_admin: boolean;
  subscription_status?: string;
  plan?: string;
  current_period_end?: number;
  credits_remaining?: number | null;
  display_name?: string | null;
};

type ByokStatus = {
  eligible?: boolean;
  has_key?: boolean;
  provider?: string | null;
};

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
  const text = await readText(res);
  return { ok: res.ok, status: res.status, text };
}

type TabKey = "profile" | "notifications" | "appearance" | "security" | "billing";

function Pill(props: { kind?: "ok" | "warn" | "bad"; children: React.ReactNode }) {
  const k = props.kind || undefined;
  return <span className={["cb-pill2", k ? k : ""].join(" ")}>{props.children}</span>;
}

export default function SettingsPage() {
  const [tab, setTab] = useState<TabKey>("profile");
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<MeOut | null>(null);
  const [topError, setTopError] = useState<string>("");
  // Profile
  const [displayName, setDisplayName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState<string>("");
  // Notifications (UI-only)
  const [notifyProduct, setNotifyProduct] = useState(true);
  const [notifySecurity, setNotifySecurity] = useState(true);
  const [notifyMarketing, setNotifyMarketing] = useState(false);
  const [notifMsg, setNotifMsg] = useState("");
  // Appearance (UI-only)
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [themeMsg, setThemeMsg] = useState("");
  // Security / password
  const [pwNew, setPwNew] = useState("");
  const [pwNew2, setPwNew2] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [pwMsg, setPwMsg] = useState("");
  // BYOK
  const [byok, setByok] = useState<ByokStatus | null>(null);
  const [byokSupported, setByokSupported] = useState<boolean | null>(null);
  const [byokLoading, setByokLoading] = useState(false);
  const [byokErr, setByokErr] = useState<string>("");
  const [byokKey, setByokKey] = useState("");
  const [byokProvider, setByokProvider] = useState<"openai" | "xai">("openai");
  const [byokBusy, setByokBusy] = useState(false);
  const [byokMsg, setByokMsg] = useState("");

  const planLabel = useMemo(() => {
    const p = (me?.plan || "").trim();
    if (!p) return "—";
    return p;
  }, [me?.plan]);

  const creditsLabel = useMemo(() => {
    const v = me?.credits_remaining;
    if (v === null || typeof v === "undefined") return "—";
    return String(v);
  }, [me?.credits_remaining]);

  const subStatusLabel = useMemo(() => {
    const s = (me?.subscription_status || "").trim();
    return s || "—";
  }, [me?.subscription_status]);

  const planPillKind = useMemo<"ok" | "warn" | "bad">(() => {
    const s = (me?.subscription_status || "").toLowerCase();
    if (!s) return "warn";
    if (s.includes("active") || s.includes("trial")) return "ok";
    if (s.includes("past_due") || s.includes("incomplete")) return "warn";
    return "bad";
  }, [me?.subscription_status]);

  async function loadMe() {
    setTopError("");
    setLoading(true);
    const who = await apiJson<MeOut>("/api/auth/whoami");
    if (who.ok && who.data) {
      setMe(who.data);
      setDisplayName((who.data.display_name || "").trim());
      setLoading(false);
      return;
    }
    const prof = await apiJson<MeOut>("/api/profile");
    if (prof.ok && prof.data) {
      setMe(prof.data);
      setDisplayName((prof.data.display_name || "").trim());
      setLoading(false);
      return;
    }
    setMe(null);
    setLoading(false);
    const status = who.status || prof.status;
    setTopError(`Failed to load account info (HTTP ${status}).`);
  }

  async function loadByok(force: boolean = false) {
    if (!force && byokSupported !== null) return;

    setByokLoading(true);
    setByokErr("");
    setByokMsg("");
    setByok(null);

    const res = await apiJson<ByokStatus>("/api/byok/status");

    if (res.ok && res.data) {
      setByok(res.data);
      setByokSupported(true);
    } else if (res.status === 404) {
      setByok(null);
      setByokErr("BYOK isn’t enabled on the backend yet (404). UI will not retry automatically.");
      setByokSupported(false);
    } else {
      setByok(null);
      setByokErr(`Failed to load BYOK status (HTTP ${res.status}).`);
      setByokSupported(false);
    }
    setByokLoading(false);
  }

  useEffect(() => {
    loadMe();
  }, []);

  useEffect(() => {
    if (tab === "security" && byokSupported === null) {
      loadByok();
    }
  }, [tab]);

  async function refreshAll() {
    await loadMe();
    if (tab === "security") {
      loadByok(true);
    }
  }

  async function saveProfile() {
    setProfileMsg("");
    setSavingProfile(true);
    try {
      const res = await apiJson<{ ok: boolean; display_name?: string }>("/api/profile", {
        method: "POST",
        body: JSON.stringify({ display_name: displayName.trim() }),
      });
      if (!res.ok) {
        setProfileMsg(`Save failed (HTTP ${res.status}).`);
        return;
      }
      setProfileMsg("Saved.");
      await loadMe();
    } finally {
      setSavingProfile(false);
    }
  }

  async function saveNotifications() {
    setNotifMsg("Saved (UI only).");
    window.setTimeout(() => setNotifMsg(""), 1500);
  }

  async function saveAppearance() {
    setThemeMsg("Saved (UI only).");
    window.setTimeout(() => setThemeMsg(""), 1500);
  }

  async function updatePassword() {
    setPwMsg("");
    if (!pwNew || pwNew.length < 8) {
      setPwMsg("Password must be at least 8 characters.");
      return;
    }
    if (pwNew !== pwNew2) {
      setPwMsg("Passwords do not match.");
      return;
    }
    setPwBusy(true);
    try {
      const res = await apiJson<{ ok: boolean; detail?: string }>("/api/auth/change_password", {
        method: "POST",
        body: JSON.stringify({ new_password: pwNew }),
      });
      if (!res.ok) {
        const msg = (res.data as any)?.detail || res.text || "";
        setPwMsg(`Failed (HTTP ${res.status}). ${String(msg).slice(0, 180)}`);
        return;
      }
      setPwMsg("Password updated.");
      setPwNew("");
      setPwNew2("");
    } finally {
      setPwBusy(false);
    }
  }

  async function saveByokKey() {
    setByokMsg("");
    if (byokSupported !== true) {
      setByokMsg("BYOK feature is not enabled.");
      return;
    }
    if (!byokKey.trim()) {
      setByokMsg("Paste a key first.");
      return;
    }
    setByokBusy(true);
    try {
      const res = await apiJson<{ ok: boolean; detail?: string }>("/api/byok/save", {
        method: "POST",
        body: JSON.stringify({ provider: byokProvider, key: byokKey.trim() }),
      });
      if (!res.ok) {
        const msg = (res.data as any)?.detail || res.text || "";
        setByokMsg(`Save failed (HTTP ${res.status}). ${String(msg).slice(0, 180)}`);
        return;
      }
      setByokKey("");
      setByokMsg("Saved.");
      await loadByok(true);
    } finally {
      setByokBusy(false);
    }
  }

  async function deleteByokKey() {
    setByokMsg("");
    if (byokSupported !== true) {
      setByokMsg("BYOK feature is not enabled.");
      return;
    }
    setByokBusy(true);
    try {
      const res = await apiJson<{ ok: boolean; detail?: string }>("/api/byok/delete", { method: "POST" });
      if (!res.ok) {
        const msg = (res.data as any)?.detail || res.text || "";
        setByokMsg(`Delete failed (HTTP ${res.status}). ${String(msg).slice(0, 180)}`);
        return;
      }
      setByokMsg("Deleted.");
      await loadByok(true);
    } finally {
      setByokBusy(false);
    }
  }

  const headerRight = (
    <div className="cb-actions">
      <Link href={`${BASE}/dashboard`} className="no-underline">
        <button className="cb-btn">← Back to Dashboard</button>
      </Link>
      <button className="cb-btn primary" onClick={refreshAll} disabled={loading}>
        Refresh
      </button>
    </div>
  );

  const byokHeadPill = byokLoading ? (
    <Pill>Loading…</Pill>
  ) : byokSupported === false ? (
    <Pill kind="warn">Not enabled</Pill>
  ) : byok?.has_key ? (
    <Pill kind="ok">Key saved</Pill>
  ) : (
    <Pill kind="warn">No key</Pill>
  );

  const tabMeta: Record<
    TabKey,
    { icon: string; title: string; desc: string; badge?: React.ReactNode }
  > = {
    profile: { icon: "👤", title: "Profile", desc: "Name + account basics" },
    notifications: { icon: "🔔", title: "Notifications", desc: "Product + security alerts", badge: <Pill kind="warn">UI-only</Pill> },
    appearance: { icon: "🎨", title: "Appearance", desc: "Theme preferences", badge: <Pill kind="warn">UI-only</Pill> },
    security: {
      icon: "🛡️",
      title: "Security",
      desc: "Password + BYOK",
      badge: byokSupported === false ? <Pill kind="warn">Disabled</Pill> : byokErr ? <Pill kind="warn">BYOK</Pill> : byok?.has_key ? <Pill kind="ok">BYOK</Pill> : undefined,
    },
    billing: { icon: "💳", title: "Plan & Billing", desc: "Upgrade + usage" },
  };

  return (
    <div className="cb-settings cb-bg">
      <div className="mx-auto w-full max-w-6xl">
        <div className="cb-card">
          <div className="cb-card__head">
            <div>
              <div className="cb-card__title">Settings</div>
              <div className="cb-card__sub">Manage your account preferences, security, and billing.</div>
            </div>
            {headerRight}
          </div>
          {topError ? (
            <div className="cb-card__body">
              <div className="cb-note" style={{ borderColor: "rgba(239,68,68,0.25)", background: "rgba(239,68,68,0.10)" }}>
                <div style={{ fontWeight: 900, marginBottom: 6 }}>Couldn’t load account</div>
                <div style={{ opacity: 0.85 }}>{topError}</div>
              </div>
            </div>
          ) : null}
          <div className="cb-card__body">
            <div className="cb-settings-grid">
              {/* LEFT: tabs + quick summary */}
              <div className="space-y-3">
                <div className="cb-tabs">
                  {(Object.keys(tabMeta) as TabKey[]).map((k) => (
                    <button
                      key={k}
                      className={["cb-tab", tab === k ? "is-active" : ""].join(" ")}
                      onClick={() => setTab(k)}
                      type="button"
                    >
                      <div style={{ fontSize: 14, opacity: 0.9 }}>{tabMeta[k].icon}</div>
                      <div className="min-w-0">
                        <div className="cb-tab__title">{tabMeta[k].title}</div>
                        <div className="cb-tab__desc">{tabMeta[k].desc}</div>
                      </div>
                      <div>{tabMeta[k].badge}</div>
                    </button>
                  ))}
                </div>
                <div className="cb-kpi">
                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label">Signed in</div>
                    <div className="cb-kpi__value">{loading ? "Loading…" : me?.email || "—"}</div>
                  </div>
                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label">Subscription</div>
                    <div className="cb-kpi__value" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {loading ? "…" : planLabel}
                      {!loading ? <Pill kind={planPillKind}>{subStatusLabel}</Pill> : null}
                    </div>
                  </div>
                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label">Credits remaining</div>
                    <div className="cb-kpi__value">{loading ? "…" : creditsLabel}</div>
                  </div>
                  <div className="cb-kpi__box">
                    <div className="cb-kpi__label">Role</div>
                    <div className="cb-kpi__value">{loading ? "…" : me?.is_admin ? "Admin" : "User"}</div>
                  </div>
                </div>
                <div className="cb-note">
                  Tip: BYOK being missing (404) should never break Settings. If it does, that’s a UI bug — not a backend issue.
                </div>
              </div>
              {/* RIGHT: panel */}
              <div className="space-y-3">
                {loading ? (
                  <div className="cb-note">Loading account data…</div>
                ) : null}
                {!loading && tab === "profile" ? (
                  <div className="cb-card">
                    <div className="cb-card__head">
                      <div>
                        <div className="cb-card__title">Profile</div>
                        <div className="cb-card__sub">Update your display name. Email cannot be changed.</div>
                      </div>
                    </div>
                    <div className="cb-card__body">
                      <div className="cb-form">
                        <div className="cb-row2">
                          <div className="cb-field">
                            <label>Display name</label>
                            <input
                              value={displayName}
                              onChange={(e) => setDisplayName(e.target.value)}
                              placeholder="Enter your name"
                              autoComplete="name"
                            />
                            <div className="cb-help">This is what appears across the builder and dashboards.</div>
                          </div>
                          <div className="cb-field">
                            <label>Email</label>
                            <input value={me?.email || ""} readOnly />
                            <div className="cb-help">Email cannot be changed.</div>
                          </div>
                        </div>
                        <div className="cb-actions">
                          <button className="cb-btn primary" onClick={saveProfile} disabled={savingProfile}>
                            {savingProfile ? "Saving…" : "Save changes"}
                          </button>
                          {profileMsg ? <div className="cb-muted" style={{ fontSize: 12 }}>{profileMsg}</div> : null}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
                {!loading && tab === "notifications" ? (
                  <div className="cb-card">
                    <div className="cb-card__head">
                      <div>
                        <div className="cb-card__title">Notifications</div>
                        <div className="cb-card__sub">UI-only for now (wire to backend when ready).</div>
                      </div>
                      <Pill kind="warn">UI-only</Pill>
                    </div>
                    <div className="cb-card__body">
                      <div className="cb-form">
                        <div className="cb-note">
                          These toggles currently save locally. When you want persistence, we’ll back them with a
                          `/api/settings` payload.
                        </div>
                        <div className="cb-field">
                          <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span>Product updates</span>
                            <input
                              type="checkbox"
                              checked={notifyProduct}
                              onChange={(e) => setNotifyProduct(e.target.checked)}
                            />
                          </label>
                        </div>
                        <div className="cb-field">
                          <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span>Security alerts</span>
                            <input
                              type="checkbox"
                              checked={notifySecurity}
                              onChange={(e) => setNotifySecurity(e.target.checked)}
                            />
                          </label>
                        </div>
                        <div className="cb-field">
                          <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span>Marketing</span>
                            <input
                              type="checkbox"
                              checked={notifyMarketing}
                              onChange={(e) => setNotifyMarketing(e.target.checked)}
                            />
                          </label>
                        </div>
                        <div className="cb-actions">
                          <button className="cb-btn primary" onClick={saveNotifications}>
                            Save changes
                          </button>
                          {notifMsg ? <div className="cb-muted" style={{ fontSize: 12 }}>{notifMsg}</div> : null}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
                {!loading && tab === "appearance" ? (
                  <div className="cb-card">
                    <div className="cb-card__head">
                      <div>
                        <div className="cb-card__title">Appearance</div>
                        <div className="cb-card__sub">Theme preferences (UI-only for now).</div>
                      </div>
                      <Pill kind="warn">UI-only</Pill>
                    </div>
                    <div className="cb-card__body">
                      <div className="cb-form">
                        <div className="cb-note">
                          You can keep dark as default. When you’re ready, we’ll persist this and optionally apply it
                          globally.
                        </div>
                        <div className="cb-field">
                          <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <input type="radio" name="theme" checked={theme === "dark"} onChange={() => setTheme("dark")} />
                            <span style={{ fontWeight: 900 }}>Dark</span>
                            <Pill kind="ok">Recommended</Pill>
                          </label>
                        </div>
                        <div className="cb-field">
                          <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <input type="radio" name="theme" checked={theme === "light"} onChange={() => setTheme("light")} />
                            <span style={{ fontWeight: 900 }}>Light</span>
                            <Pill kind="warn">Optional</Pill>
                          </label>
                        </div>
                        <div className="cb-actions">
                          <button className="cb-btn primary" onClick={saveAppearance}>
                            Save changes
                          </button>
                          {themeMsg ? <div className="cb-muted" style={{ fontSize: 12 }}>{themeMsg}</div> : null}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
                {!loading && tab === "security" ? (
                  <>
                    <div className="cb-card">
                      <div className="cb-card__head">
                        <div>
                          <div className="cb-card__title">Password</div>
                          <div className="cb-card__sub">
                            OAuth-only accounts may be blocked by backend for password changes.
                          </div>
                        </div>
                      </div>
                      <div className="cb-card__body">
                        <div className="cb-form">
                          <div className="cb-row2">
                            <div className="cb-field">
                              <label>New password</label>
                              <input
                                type="password"
                                value={pwNew}
                                onChange={(e) => setPwNew(e.target.value)}
                                placeholder="Min 8 characters"
                                autoComplete="new-password"
                              />
                            </div>
                            <div className="cb-field">
                              <label>Confirm new password</label>
                              <input
                                type="password"
                                value={pwNew2}
                                onChange={(e) => setPwNew2(e.target.value)}
                                placeholder="Re-enter password"
                                autoComplete="new-password"
                              />
                            </div>
                          </div>
                          <div className="cb-actions">
                            <button className="cb-btn primary" onClick={updatePassword} disabled={pwBusy}>
                              {pwBusy ? "Updating…" : "Update password"}
                            </button>
                            {pwMsg ? <div className="cb-muted" style={{ fontSize: 12 }}>{pwMsg}</div> : null}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="cb-card">
                      <div className="cb-card__head">
                        <div>
                          <div className="cb-card__title">Bring your own key (BYOK)</div>
                          <div className="cb-card__sub">Available only if backend enables it for your plan/admin.</div>
                        </div>
                        {byokHeadPill}
                      </div>
                      <div className="cb-card__body">
                        <div className="cb-form">
                          {byokLoading && <div className="cb-note">Checking BYOK availability…</div>}
                          {byokSupported === false ? (
                            <div className="cb-note" style={{ borderColor: "rgba(239,68,68,0.25)", background: "rgba(239,68,68,0.10)" }}>
                              <div style={{ fontWeight: 900 }}>BYOK not enabled yet</div>
                              <div>The backend endpoints for Bring Your Own Key are not implemented. The feature will appear automatically when they are added.</div>
                            </div>
                          ) : (
                            <>
                              {byokErr && <div className="cb-note">{byokErr}</div>}
                              <div className="cb-row2">
                                <div className="cb-field">
                                  <label>Provider</label>
                                  <select
                                    value={byokProvider}
                                    onChange={(e) => setByokProvider(e.target.value as any)}
                                  >
                                    <option value="openai">openai</option>
                                    <option value="xai">xai</option>
                                  </select>
                                  <div className="cb-help">
                                    Current status:{" "}
                                    <span style={{ fontWeight: 900 }}>
                                      {byok ? (byok.has_key ? "Key saved" : "No key saved") : "—"}
                                    </span>
                                  </div>
                                </div>
                                <div className="cb-field">
                                  <label>API key</label>
                                  <input
                                    type="password"
                                    value={byokKey}
                                    onChange={(e) => setByokKey(e.target.value)}
                                    placeholder="Paste API key…"
                                    autoComplete="off"
                                  />
                                  <div className="cb-help">Stored server-side (not displayed again after save).</div>
                                </div>
                              </div>
                              <div className="cb-actions">
                                <button
                                  className="cb-btn primary"
                                  disabled={byokBusy || byokLoading || !byokKey.trim()}
                                  onClick={saveByokKey}
                                >
                                  {byokBusy ? "Saving…" : "Save key"}
                                </button>
                                <button
                                  className="cb-btn danger"
                                  disabled={byokBusy || byokLoading || !(byok?.has_key)}
                                  onClick={deleteByokKey}
                                >
                                  Delete key
                                </button>
                                <button className="cb-btn" disabled={byokBusy || byokLoading} onClick={() => loadByok(true)}>
                                  Refresh status
                                </button>
                                {byokMsg ? <div className="cb-muted" style={{ fontSize: 12 }}>{byokMsg}</div> : null}
                              </div>
                              {byok && typeof byok.eligible !== "undefined" ? (
                                <div className="cb-note">
                                  Eligibility:{" "}
                                  <span style={{ fontWeight: 900 }}>
                                    {byok.eligible ? "Eligible" : "Not eligible"}
                                  </span>
                                  {byok.eligible ? "" : " (upgrade plan or ask admin access)"}
                                </div>
                              ) : null}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </>
                ) : null}
                {!loading && tab === "billing" ? (
                  <div className="cb-card">
                    <div className="cb-card__head">
                      <div>
                        <div className="cb-card__title">Plan & Billing</div>
                        <div className="cb-card__sub">Upgrade your plan and view usage.</div>
                      </div>
                    </div>
                    <div className="cb-card__body">
                      <div className="cb-form">
                        <div className="cb-kpi">
                          <div className="cb-kpi__box">
                            <div className="cb-kpi__label">Current plan</div>
                            <div className="cb-kpi__value" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                              {planLabel}
                              <Pill kind={planPillKind}>{subStatusLabel}</Pill>
                            </div>
                          </div>
                          <div className="cb-kpi__box">
                            <div className="cb-kpi__label">Credits remaining</div>
                            <div className="cb-kpi__value">{creditsLabel}</div>
                          </div>
                          <div className="cb-kpi__box">
                            <div className="cb-kpi__label">Renewal</div>
                            <div className="cb-kpi__value">
                              {me?.current_period_end
                                ? new Date(me.current_period_end * 1000).toLocaleString()
                                : "—"}
                            </div>
                          </div>
                          <div className="cb-kpi__box">
                            <div className="cb-kpi__label">Account</div>
                            <div className="cb-kpi__value">{me?.is_admin ? "Admin access" : "Standard access"}</div>
                          </div>
                        </div>
                        <div className="cb-divider" />
                        <div className="cb-note">
                          If upgrade isn’t wired yet, that’s backend routing + Stripe checkout wiring. The UI is ready
                          and won’t break other tabs.
                        </div>
                        <div className="cb-actions">
                          <Link href={`${BASE}/account`} className="no-underline">
                            <button className="cb-btn">Manage account</button>
                          </Link>
                          <Link href={`${BASE}/account/upgrade`} className="no-underline">
                            <button className="cb-btn primary">Upgrade plan</button>
                          </Link>
                          <Link href={`${BASE}/dashboard`} className="no-underline">
                            <button className="cb-btn">Go to dashboard</button>
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}