"use client";

import React, { useEffect, useMemo, useState } from "react";

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
  const text = await res.text().catch(() => "");
  return { ok: res.ok, status: res.status, text };
}

type TabKey = "profile" | "notifications" | "appearance" | "security" | "billing" | "stripe" | "admin";

function StripeConnectPanel() {
  const cardStyle: React.CSSProperties = { padding: 16, borderRadius: 12, background: "rgba(255,255,255,0.03)", marginBottom: 12 };

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "white", marginBottom: 6 }}>Stripe Connect — Coming Soon</h2>
      <p style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", marginBottom: 20, lineHeight: 1.5 }}>
        Connect your Stripe account so CodeBot can integrate your real products and payment links into generated websites.
      </p>

      <div style={{ ...cardStyle, border: "1px solid rgba(255,193,7,0.25)", background: "rgba(255,193,7,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,193,7,0.95)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Coming Soon</span>
        </div>
        <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>
          Stripe Connect is in the pipeline. You’ll soon be able to link your Stripe account and use your real products inside sites built with CodeBot. Check back later.
        </div>
      </div>
    </div>
  );
}

function Pill({ tone = "neutral", children }: { tone?: "ok" | "warn" | "neutral"; children: React.ReactNode }) {
  const bg = tone === "ok" ? "rgba(34,197,94,0.12)" : tone === "warn" ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.06)";
  const color = tone === "ok" ? "rgba(134,239,172,1)" : tone === "warn" ? "rgba(253,224,71,1)" : "rgba(255,255,255,0.6)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "4px 12px", fontSize: 11, fontWeight: 700, background: bg, color }}>{children}</span>
  );
}

const tabDefs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: "profile", label: "Profile", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg> },
  { key: "notifications", label: "Notifications", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg> },
  { key: "appearance", label: "Appearance", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg> },
  { key: "security", label: "Security", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg> },
  { key: "billing", label: "Plan & Billing", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" /></svg> },
  { key: "stripe", label: "Stripe Connect — Coming Soon", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 13h4l-1 9 10-12h-4l3-8z" /></svg> },
  { key: "admin", label: "Admin — Pipeline", icon: <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg> },
];

const s = {
  page: { minHeight: "100vh", background: "var(--cb-bg, #0b0f14)", color: "white", padding: "48px 0" } as React.CSSProperties,
  wrap: { maxWidth: 1200, margin: "0 auto", padding: "0 32px" } as React.CSSProperties,
  header: { marginBottom: 40, display: "flex", flexWrap: "wrap" as const, alignItems: "center", justifyContent: "space-between", gap: 20 } as React.CSSProperties,
  h1: { fontSize: 28, fontWeight: 700, color: "white", margin: 0, lineHeight: 1.2 } as React.CSSProperties,
  sub: { fontSize: 14, color: "rgba(255,255,255,0.5)", marginTop: 6 } as React.CSSProperties,
  btnGroup: { display: "flex", gap: 8 } as React.CSSProperties,
  btnGhost: { height: 38, padding: "0 16px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.75)", fontSize: 13, fontWeight: 600, cursor: "pointer", textDecoration: "none" } as React.CSSProperties,
  btnPrimary: { height: 38, padding: "0 16px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.92)", color: "rgba(0,0,0,0.9)", fontSize: 13, fontWeight: 600, cursor: "pointer" } as React.CSSProperties,
  grid: { display: "grid", gridTemplateColumns: "240px 1fr", gap: 24 } as React.CSSProperties,
  nav: { borderRadius: 14, background: "rgba(255,255,255,0.02)", boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)", padding: 10, position: "sticky" as const, top: 24 } as React.CSSProperties,
  navBtn: (active: boolean) => ({
    width: "100%",
    textAlign: "left" as const,
    padding: "10px 14px",
    borderRadius: 10,
    border: "none",
    background: active ? "rgba(255,255,255,0.08)" : "transparent",
    color: active ? "white" : "rgba(255,255,255,0.6)",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: 10,
  }) as React.CSSProperties,
  card: { borderRadius: 14, background: "rgba(255,255,255,0.02)", boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)", padding: 36 } as React.CSSProperties,
  section: { marginBottom: 32 } as React.CSSProperties,
  h2: { fontSize: 20, fontWeight: 700, color: "white", margin: "0 0 6px" } as React.CSSProperties,
  desc: { fontSize: 14, color: "rgba(255,255,255,0.5)", margin: "0 0 24px" } as React.CSSProperties,
  label: { display: "block", fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", marginBottom: 8 } as React.CSSProperties,
  input: {
    width: "100%",
    boxSizing: "border-box" as const,
    height: 44,
    padding: "0 14px",
    borderRadius: 10,
    border: "none",
    background: "rgba(0,0,0,0.3)",
    color: "rgba(255,255,255,0.9)",
    fontSize: 14,
    outline: "none",
    fontFamily: "inherit",
  } as React.CSSProperties,
  inputRo: {
    width: "100%",
    boxSizing: "border-box" as const,
    height: 44,
    padding: "0 14px",
    borderRadius: 10,
    border: "none",
    background: "rgba(0,0,0,0.2)",
    color: "rgba(255,255,255,0.5)",
    fontSize: 14,
    cursor: "not-allowed",
    fontFamily: "inherit",
  } as React.CSSProperties,
  select: {
    width: "100%",
    boxSizing: "border-box" as const,
    height: 44,
    padding: "0 14px",
    borderRadius: 10,
    border: "none",
    background: "rgba(0,0,0,0.3)",
    color: "rgba(255,255,255,0.9)",
    fontSize: 14,
    cursor: "pointer",
    fontFamily: "inherit",
    outline: "none",
  } as React.CSSProperties,
  hint: { fontSize: 12, color: "rgba(255,255,255,0.35)", marginTop: 6 } as React.CSSProperties,
  fieldGap: { height: 18 } as React.CSSProperties,
  saveRow: { display: "flex", alignItems: "center", gap: 12, marginTop: 20 } as React.CSSProperties,
  msgOk: { fontSize: 13, color: "rgba(134,239,172,1)" } as React.CSSProperties,
  msgErr: { fontSize: 13, color: "#ff4d4d" } as React.CSSProperties,
  toggle: (on: boolean) => ({
    display: "flex",
    alignItems: "flex-start",
    gap: 14,
    padding: 16,
    borderRadius: 12,
    background: on ? "rgba(255,255,255,0.04)" : "transparent",
    cursor: "pointer",
  }) as React.CSSProperties,
  checkbox: { width: 18, height: 18, marginTop: 2, accentColor: "#3b82f6", cursor: "pointer" } as React.CSSProperties,
  radio: (on: boolean) => ({
    display: "flex",
    alignItems: "flex-start",
    gap: 14,
    padding: 16,
    borderRadius: 12,
    background: on ? "rgba(255,255,255,0.04)" : "transparent",
    cursor: "pointer",
  }) as React.CSSProperties,
  sectionDivider: { height: 1, background: "rgba(255,255,255,0.04)", margin: "28px 0" } as React.CSSProperties,
  subsectionTitle: { fontSize: 16, fontWeight: 600, color: "white", margin: "0 0 20px", paddingBottom: 12, borderBottom: "1px solid rgba(255,255,255,0.04)" } as React.CSSProperties,
  infoBox: (tone: "amber" | "blue") => ({
    padding: 14,
    borderRadius: 10,
    background: tone === "amber" ? "rgba(245,158,11,0.1)" : "rgba(59,130,246,0.1)",
    color: tone === "amber" ? "rgba(253,224,71,1)" : "rgba(147,197,253,1)",
    fontSize: 13,
  }) as React.CSSProperties,
  errBox: {
    marginBottom: 24,
    padding: "14px 16px",
    borderRadius: 10,
    background: "rgba(255,77,77,0.08)",
    color: "#ff4d4d",
    fontSize: 14,
  } as React.CSSProperties,
  acctBlock: { padding: "16px 14px", borderTop: "1px solid rgba(255,255,255,0.04)", marginTop: 16 } as React.CSSProperties,
};

export default function SettingsPage() {
  const [tab, setTab] = useState<TabKey>("profile");
  const [me, setMe] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [topError, setTopError] = useState("");

  const [displayName, setDisplayName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  const [notifyProduct, setNotifyProduct] = useState(true);
  const [notifySecurity, setNotifySecurity] = useState(true);
  const [notifyMarketing, setNotifyMarketing] = useState(false);

  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const [pwNew, setPwNew] = useState("");
  const [pwNew2, setPwNew2] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [pwMsg, setPwMsg] = useState("");

  const [byok, setByok] = useState<ByokStatus | null>(null);
  const [byokSupported, setByokSupported] = useState<boolean | null>(null);
  const [byokLoading, setByokLoading] = useState(false);
  const [byokKey, setByokKey] = useState("");
  const [byokProvider, setByokProvider] = useState<"openai" | "xai">("openai");
  const [byokMsg, setByokMsg] = useState("");

  const [adminXaiKey, setAdminXaiKey] = useState("");
  const [adminXaiModel, setAdminXaiModel] = useState("grok-4-1-fast");
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminMsg, setAdminMsg] = useState("");
  const [adminCurrentKey, setAdminCurrentKey] = useState("");
  const [adminCurrentModel, setAdminCurrentModel] = useState("");

  const planStatus = useMemo(() => {
    const st = (me?.subscription_status || "").toLowerCase();
    if (st.includes("active") || st.includes("trial")) return "ok";
    return "warn";
  }, [me?.subscription_status]);

  async function loadMe() {
    setLoading(true);
    setTopError("");
    const res = await apiJson<MeOut>("/api/auth/whoami");
    if (res.ok && res.data) {
      setMe(res.data);
      setDisplayName(res.data.display_name || "");
      setLoading(false);
      return;
    }
    setTopError(`Failed to load account (HTTP ${res.status}).`);
    setLoading(false);
  }

  async function loadByok() {
    if (byokSupported !== null) return;
    setByokLoading(true);
    const res = await apiJson<ByokStatus>("/api/byok/status");
    if (res.ok && res.data) { setByok(res.data); setByokSupported(true); }
    else if (res.status === 404) { setByokSupported(false); }
    setByokLoading(false);
  }

  useEffect(() => { loadMe(); }, []);
  useEffect(() => { if (tab === "security") loadByok(); }, [tab]);

  async function saveProfile() {
    setSavingProfile(true);
    setProfileMsg("");
    const res = await apiJson("/api/profile", { method: "POST", body: JSON.stringify({ display_name: displayName.trim() }) });
    setSavingProfile(false);
    if (!res.ok) { setProfileMsg("Save failed."); return; }
    setProfileMsg("Saved.");
    loadMe();
  }

  async function updatePassword() {
    setPwMsg("");
    if (pwNew.length < 8) { setPwMsg("Password must be at least 8 characters."); return; }
    if (pwNew !== pwNew2) { setPwMsg("Passwords do not match."); return; }
    setPwBusy(true);
    const res = await apiJson("/api/auth/change_password", { method: "POST", body: JSON.stringify({ new_password: pwNew }) });
    setPwBusy(false);
    setPwMsg(res.ok ? "Password updated." : "Update failed.");
    if (res.ok) { setPwNew(""); setPwNew2(""); }
  }

  async function saveByok() {
    setByokMsg("");
    const res = await apiJson("/api/byok/save", { method: "POST", body: JSON.stringify({ provider: byokProvider, key: byokKey }) });
    setByokMsg(res.ok ? "Saved." : "Save failed.");
    if (res.ok) { setByokKey(""); loadByok(); }
  }

  async function loadAdminConfig() {
    const res = await apiJson<{ xai_key_masked?: string; xai_model?: string }>("/api/admin/pipeline-config");
    if (res.ok && res.data) {
      setAdminCurrentKey(res.data.xai_key_masked || "");
      setAdminCurrentModel(res.data.xai_model || "");
      if (res.data.xai_model) setAdminXaiModel(res.data.xai_model);
    }
  }

  async function saveAdminConfig() {
    setAdminSaving(true);
    setAdminMsg("");
    const body: any = { model: adminXaiModel };
    if (adminXaiKey.trim()) body.xai_key = adminXaiKey.trim();
    const res = await apiJson("/api/admin/pipeline-config", { method: "POST", body: JSON.stringify(body) });
    setAdminSaving(false);
    if (res.ok) { setAdminMsg("Saved. Backend restarting..."); setAdminXaiKey(""); loadAdminConfig(); }
    else setAdminMsg(`Save failed: ${(res.data as any)?.error || res.text || "unknown"}`);
  }

  useEffect(() => { if (tab === "admin" && me?.is_admin) loadAdminConfig(); }, [tab, me?.is_admin]);

  return (
    <div style={s.page}>
      <div style={s.wrap}>
        {/* Header */}
        <div style={s.header}>
          <div>
            <h1 style={s.h1}>Settings</h1>
            <div style={s.sub}>Account configuration and security</div>
          </div>
          <div style={s.btnGroup}>
            <a href={`${BASE}/dashboard`} style={{ ...s.btnGhost, display: "inline-flex", alignItems: "center" }}>
              ← Dashboard
            </a>
            <button type="button" style={s.btnPrimary} onClick={loadMe} disabled={loading}>
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>

        {topError ? <div style={s.errBox}>{topError}</div> : null}

        <div style={s.grid}>
          {/* Sidebar nav */}
          <div>
            <nav style={s.nav}>
              {tabDefs.filter((t) => t.key !== "admin" || me?.is_admin).map((t) => (
                <button key={t.key} type="button" style={s.navBtn(tab === t.key)} onClick={() => setTab(t.key)}>
                  <span style={{ opacity: tab === t.key ? 1 : 0.5, display: "flex" }}>{t.icon}</span>
                  {t.label}
                  {t.key === "admin" && <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 4, background: "rgba(245,158,11,0.15)", color: "rgba(253,224,71,1)", fontWeight: 700, marginLeft: "auto" }}>ADMIN</span>}
                </button>
              ))}

              <div style={s.acctBlock}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.35)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 10 }}>Account</div>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", wordBreak: "break-all", marginBottom: 6 }}>{me?.email || "—"}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.4)" }}>Plan:</span>
                  <Pill tone={planStatus as any}>{me?.plan || "—"}</Pill>
                </div>
              </div>
            </nav>
          </div>

          {/* Content */}
          <div>
            <div style={s.card}>
              {/* PROFILE */}
              {tab === "profile" && (
                <div>
                  <h2 style={s.h2}>Profile</h2>
                  <p style={s.desc}>Manage your personal information</p>

                  <div>
                    <label style={s.label}>Display name</label>
                    <input style={s.input} value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Enter your display name" />
                  </div>
                  <div style={s.fieldGap} />
                  <div>
                    <label style={s.label}>Email</label>
                    <input style={s.inputRo} value={me?.email || ""} readOnly />
                    <div style={s.hint}>Email cannot be changed</div>
                  </div>
                  <div style={s.saveRow}>
                    <button type="button" style={s.btnPrimary} onClick={saveProfile} disabled={savingProfile}>
                      {savingProfile ? "Saving..." : "Save changes"}
                    </button>
                    {profileMsg ? <span style={profileMsg.includes("Saved") ? s.msgOk : s.msgErr}>{profileMsg}</span> : null}
                  </div>
                </div>
              )}

              {/* NOTIFICATIONS */}
              {tab === "notifications" && (
                <div>
                  <h2 style={s.h2}>Notifications</h2>
                  <p style={s.desc}>Choose what updates you receive</p>

                  {([
                    [notifyProduct, setNotifyProduct, "Product updates", "New features and improvements"] as const,
                    [notifySecurity, setNotifySecurity, "Security alerts", "Important security notifications"] as const,
                    [notifyMarketing, setNotifyMarketing, "Marketing", "Promotional content and offers"] as const,
                  ]).map(([checked, setter, title, desc], i) => (
                    <label key={i} style={s.toggle(checked)}>
                      <input type="checkbox" checked={checked} onChange={() => setter(!checked)} style={s.checkbox} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "white", marginBottom: 4 }}>{title}</div>
                        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>{desc}</div>
                      </div>
                    </label>
                  ))}

                  <div style={{ ...s.hint, marginTop: 16 }}>Notification preferences are UI-only for now</div>
                </div>
              )}

              {/* APPEARANCE */}
              {tab === "appearance" && (
                <div>
                  <h2 style={s.h2}>Appearance</h2>
                  <p style={s.desc}>Customize how CodeBot looks</p>

                  {[
                    { value: "dark" as const, title: "Dark", desc: "Reduced eye strain for low-light environments" },
                    { value: "light" as const, title: "Light", desc: "Light mode for bright environments" },
                  ].map((item) => (
                    <label key={item.value} style={s.radio(theme === item.value)}>
                      <input type="radio" checked={theme === item.value} onChange={() => setTheme(item.value)} style={{ ...s.checkbox, borderRadius: "50%" }} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "white", marginBottom: 4 }}>{item.title}</div>
                        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>{item.desc}</div>
                      </div>
                    </label>
                  ))}

                  <div style={{ ...s.hint, marginTop: 16 }}>Theme preference is UI-only for now</div>
                </div>
              )}

              {/* SECURITY */}
              {tab === "security" && (
                <div>
                  <h2 style={s.h2}>Security</h2>
                  <p style={s.desc}>Manage your password and API keys</p>

                  <h3 style={s.subsectionTitle}>Change Password</h3>
                  <div>
                    <label style={s.label}>New password</label>
                    <input type="password" style={s.input} value={pwNew} onChange={(e) => setPwNew(e.target.value)} placeholder="Min 8 characters" />
                  </div>
                  <div style={s.fieldGap} />
                  <div>
                    <label style={s.label}>Confirm password</label>
                    <input type="password" style={s.input} value={pwNew2} onChange={(e) => setPwNew2(e.target.value)} placeholder="Confirm new password" />
                  </div>
                  <div style={s.saveRow}>
                    <button type="button" style={s.btnPrimary} onClick={updatePassword} disabled={pwBusy}>
                      {pwBusy ? "Updating..." : "Update password"}
                    </button>
                    {pwMsg ? <span style={pwMsg.includes("updated") ? s.msgOk : s.msgErr}>{pwMsg}</span> : null}
                  </div>

                  <div style={s.sectionDivider} />

                  <h3 style={s.subsectionTitle}>Bring Your Own Key (BYOK)</h3>
                  {byokSupported === false ? (
                    <div style={s.infoBox("amber")}>BYOK is not currently enabled for your account</div>
                  ) : (
                    <div>
                      <div>
                        <label style={s.label}>AI Provider</label>
                        <select style={s.select} value={byokProvider} onChange={(e) => setByokProvider(e.target.value as any)}>
                          <option value="openai">OpenAI</option>
                          <option value="xai">xAI (Grok)</option>
                        </select>
                      </div>
                      <div style={s.fieldGap} />
                      <div>
                        <label style={s.label}>API Key</label>
                        <input type="password" style={{ ...s.input, fontFamily: "ui-monospace, SFMono-Regular, monospace" }} value={byokKey} onChange={(e) => setByokKey(e.target.value)} placeholder="Paste your API key" />
                        <div style={s.hint}>Your key is encrypted and stored securely</div>
                      </div>
                      <div style={s.saveRow}>
                        <button type="button" style={s.btnPrimary} onClick={saveByok}>Save API key</button>
                        {byokMsg ? <span style={byokMsg.includes("Saved") ? s.msgOk : s.msgErr}>{byokMsg}</span> : null}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* BILLING */}
              {tab === "billing" && (
                <div>
                  <h2 style={s.h2}>Plan & Billing</h2>
                  <p style={s.desc}>Manage your subscription and credits</p>

                  <div
                    style={{
                      padding: 20,
                      borderRadius: 14,
                      background: "rgba(255,255,255,0.03)",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 16,
                    }}
                  >
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 10,
                        background: "rgba(59,130,246,0.12)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="rgba(147,197,253,1)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
                      </svg>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 6 }}>Full Billing Management</div>
                      <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 14, lineHeight: 1.5 }}>
                        View subscription details, manage credits, and update payment methods on the Account page.
                      </div>
                      <a href={`${BASE}/account`} style={{ ...s.btnPrimary, display: "inline-flex", alignItems: "center", textDecoration: "none", padding: "0 16px", height: 38 }}>
                        Go to Billing & Credits →
                      </a>
                    </div>
                  </div>
                </div>
              )}

              {/* STRIPE CONNECT */}
              {tab === "stripe" && (
                <StripeConnectPanel />
              )}

              {/* ADMIN — Pipeline */}
              {tab === "admin" && me?.is_admin && (
                <div>
                  <h2 style={s.h2}>Pipeline Configuration</h2>
                  <p style={s.desc}>Admin-only. Configure the AI pipeline for testing and production.</p>

                  <div style={s.infoBox("amber")}>
                    This section is only visible to admin accounts. Changes here affect the live pipeline for all users.
                  </div>

                  <div style={s.sectionDivider} />

                  <h3 style={s.subsectionTitle}>Current Configuration</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
                    <div style={{ padding: 16, borderRadius: 12, background: "rgba(0,0,0,0.15)" }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Active API Key</div>
                      <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", fontFamily: "ui-monospace, SFMono-Regular, monospace", wordBreak: "break-all" }}>{adminCurrentKey || "Not set"}</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 12, background: "rgba(0,0,0,0.15)" }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Active Model</div>
                      <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>{adminCurrentModel || "Not set"}</div>
                    </div>
                  </div>

                  <h3 style={s.subsectionTitle}>Update Pipeline</h3>
                  <div>
                    <label style={s.label}>xAI API Key</label>
                    <input type="password" style={{ ...s.input, fontFamily: "ui-monospace, SFMono-Regular, monospace" }} value={adminXaiKey} onChange={(e) => setAdminXaiKey(e.target.value)} placeholder="xai-... (leave blank to keep current)" />
                    <div style={s.hint}>Stored in the server .env. This key is used globally for Build, Plan, Ask, and image generation when users do not have their own key (BYOK).</div>
                  </div>
                  <div style={s.fieldGap} />
                  <div>
                    <label style={s.label}>Default Model</label>
                    <select style={s.select} value={adminXaiModel} onChange={(e) => setAdminXaiModel(e.target.value)}>
                      <optgroup label="xAI Grok 4.1">
                        <option value="grok-4-1-fast">grok-4-1-fast (alias)</option>
                        <option value="grok-4-1-fast-reasoning">grok-4-1-fast-reasoning</option>
                        <option value="grok-4-1-fast-non-reasoning">grok-4-1-fast-non-reasoning</option>
                      </optgroup>
                      <optgroup label="xAI Grok 4">
                        <option value="grok-4-fast-reasoning">grok-4-fast-reasoning</option>
                        <option value="grok-4-fast-non-reasoning">grok-4-fast-non-reasoning</option>
                      </optgroup>
                      <optgroup label="xAI Code">
                        <option value="grok-code-fast-1">grok-code-fast-1</option>
                      </optgroup>
                      <optgroup label="xAI Legacy">
                        <option value="grok-3">grok-3</option>
                        <option value="grok-3-mini">grok-3-mini</option>
                      </optgroup>
                    </select>
                  </div>
                  <div style={s.saveRow}>
                    <button type="button" style={s.btnPrimary} onClick={saveAdminConfig} disabled={adminSaving}>{adminSaving ? "Saving..." : "Save & Apply"}</button>
                    {adminMsg && <span style={adminMsg.includes("Saved") ? s.msgOk : s.msgErr}>{adminMsg}</span>}
                  </div>

                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
