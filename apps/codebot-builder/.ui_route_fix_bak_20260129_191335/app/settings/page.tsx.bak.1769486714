"use client";

import React, { useEffect, useMemo, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { useSearchParams } from "next/navigation";

const BASE = "/codebot";

type TabKey = "profile" | "notifications" | "appearance" | "security";

type MeOut = {
  id: string;
  email: string;
  is_admin: boolean;
  subscription_status: string;
  plan: string;
  current_period_end: number;
  credits_remaining?: number | null;
};

type ApiKeyStatus = { has_key: boolean; provider?: string | null };

async function readText(res: Response): Promise<string> {
  return await res.text().catch(() => "");
}

function cx(...s: Array<string | false | null | undefined>) {
  return s.filter(Boolean).join(" ");
}

export default function SettingsPage() {
  const sp = useSearchParams();
  const initialTab = (sp.get("tab") || "profile").toLowerCase() as TabKey;

  const [activeTab, setActiveTab] = useState<TabKey>(
    ["profile", "notifications", "appearance", "security"].includes(initialTab) ? initialTab : "profile"
  );

  // --- shared ui state ---
  const [pageErr, setPageErr] = useState<string | null>(null);
  const [pageOk, setPageOk] = useState<string | null>(null);

  // --- profile ---
  const [meLoading, setMeLoading] = useState(true);
  const [me, setMe] = useState<MeOut | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // --- security: password ---
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  // --- security: BYOK ---
  const [byokLoading, setByokLoading] = useState(true);
  const [byokStatus, setByokStatus] = useState<ApiKeyStatus | null>(null);
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);

  const canSaveKey = useMemo(() => apiKey.trim().length >= 10 && !savingKey, [apiKey, savingKey]);

  // keep tab in sync if URL changes
  useEffect(() => {
    const t = (sp.get("tab") || "profile").toLowerCase();
    if (t === activeTab) return;
    if (t === "profile" || t === "notifications" || t === "appearance" || t === "security") {
      setActiveTab(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp]);

  function setOk(msg: string) {
    setPageErr(null);
    setPageOk(msg);
    window.setTimeout(() => setPageOk(null), 2500);
  }
  function setErr(msg: string) {
    setPageOk(null);
    setPageErr(msg);
  }

  async function loadMe() {
    setPageErr(null);
    const res = await fetch(`${BASE}/api/me`, { method: "GET", credentials: "include" });
    if (res.status === 401) {
      window.location.assign(`${BASE}/login`);
      return;
    }
    if (!res.ok) {
      const t = await readText(res);
      setErr(`Failed to load profile (HTTP ${res.status}). ${t || ""}`.trim());
      return;
    }
    const data = (await res.json()) as MeOut;
    setMe(data);
    setMeLoading(false);
  }

  async function saveProfile() {
    setPageErr(null);
    setPageOk(null);

    const dn = displayName.trim();
    if (!dn) return setErr("Display name cannot be empty.");

    setSavingProfile(true);
    try {
      // Backend route: routes/settings.py -> POST {API_PREFIX}/profile
      const res = await fetch(`${BASE}/api/profile`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ display_name: dn }),
      });

      if (res.status === 401) {
        window.location.assign(`${BASE}/login`);
        return;
      }
      if (!res.ok) {
        const t = await readText(res);
        setErr(`Save failed (HTTP ${res.status}). ${t || ""}`.trim());
        return;
      }

      setOk("Saved changes.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword() {
    setPageErr(null);
    setPageOk(null);

    if (!curPw.trim() || !newPw.trim()) return setErr("Enter current and new password.");
    if (newPw.trim().length < 8) return setErr("New password must be at least 8 characters.");

    setSavingPw(true);
    try {
      // Backend route: routes/settings.py -> POST {API_PREFIX}/auth/change-password
      const res = await fetch(`${BASE}/api/auth/change-password`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ current_password: curPw, new_password: newPw }),
      });

      if (res.status === 401) {
        window.location.assign(`${BASE}/login`);
        return;
      }
      if (!res.ok) {
        const t = await readText(res);
        setErr(`Password change failed (HTTP ${res.status}). ${t || ""}`.trim());
        return;
      }

      setCurPw("");
      setNewPw("");
      setOk("Password updated.");
    } finally {
      setSavingPw(false);
    }
  }

  async function loadByok() {
    setPageErr(null);
    setPageOk(null);

    const res = await fetch(`${BASE}/api/api-key`, { method: "GET", credentials: "include" });
    if (res.status === 401) {
      window.location.assign(`${BASE}/login`);
      return;
    }
    if (!res.ok) {
      const t = await readText(res);
      setErr(`Failed to load BYOK status (HTTP ${res.status}). ${t || ""}`.trim());
      return;
    }

    const data = (await res.json()) as ApiKeyStatus;
    setByokStatus(data);
    if (data?.provider) setProvider(data.provider);
  }

  async function saveKey() {
    setPageErr(null);
    setPageOk(null);
    if (!canSaveKey) return;

    setSavingKey(true);
    try {
      const res = await fetch(`${BASE}/api/api-key`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey.trim() }),
      });

      if (res.status === 401) {
        window.location.assign(`${BASE}/login`);
        return;
      }
      if (!res.ok) {
        const t = await readText(res);
        setErr(`Save failed (HTTP ${res.status}). ${t || ""}`.trim());
        return;
      }

      setApiKey("");
      setOk("API key saved.");
      await loadByok();
    } finally {
      setSavingKey(false);
    }
  }

  async function deleteKey() {
    setPageErr(null);
    setPageOk(null);

    setDeletingKey(true);
    try {
      const res = await fetch(`${BASE}/api/api-key`, { method: "DELETE", credentials: "include" });

      if (res.status === 401) {
        window.location.assign(`${BASE}/login`);
        return;
      }
      if (!res.ok) {
        const t = await readText(res);
        setErr(`Delete failed (HTTP ${res.status}). ${t || ""}`.trim());
        return;
      }

      setOk("API key deleted.");
      await loadByok();
    } finally {
      setDeletingKey(false);
    }
  }

  useEffect(() => {
    (async () => {
      setMeLoading(true);
      setByokLoading(true);
      try {
        await loadMe();
        await loadByok();
      } finally {
        setMeLoading(false);
        setByokLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tabBtn = (key: TabKey, label: string, icon: string) => {
    const active = activeTab === key;
    return (
      <button
        type="button"
        onClick={() => {
          setActiveTab(key);
          const u = new URL(window.location.href);
          u.pathname = `${BASE}/settings`;
          u.searchParams.set("tab", key);
          window.history.replaceState({}, "", u.toString());
        }}
        className={cx(
          "w-full rounded-xl px-4 py-3 text-left text-sm font-medium transition",
          active ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
        )}
      >
        <span className="mr-2 inline-block w-5 text-white/70">{icon}</span>
        {label}
      </button>
    );
  };

  return (
    <AuthGate redirectTo="/codebot/login" allowCookieSessionFallback={true}>
      <div className="min-h-screen cb-bg text-white">
        <div className="mx-auto max-w-6xl px-8 py-10">
          {/* header */}
          <button
            type="button"
            onClick={() => window.location.assign(`${BASE}/dashboard`)}
            className="mb-6 inline-flex items-center gap-2 text-sm text-white/60 hover:text-white"
          >
            <span aria-hidden>←</span> Back to Dashboard
          </button>

          <div className="mb-8">
            <div className="text-3xl font-semibold">Settings</div>
            <div className="mt-1 text-sm text-white/60">Manage your account preferences and settings</div>
          </div>

          {pageErr ? (
            <div className="mb-6 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {pageErr}
            </div>
          ) : null}
          {pageOk ? (
            <div className="mb-6 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              {pageOk}
            </div>
          ) : null}

          <div className="grid gap-8 md:grid-cols-[280px_1fr]">
            {/* left tabs */}
            <div className="h-fit rounded-2xl border border-white/10 bg-white/5 p-3">
              {tabBtn("profile", "Profile", "👤")}
              {tabBtn("notifications", "Notifications", "🔔")}
              {tabBtn("appearance", "Appearance", "🎨")}
              {tabBtn("security", "Security", "🛡️")}
            </div>

            {/* right content */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              {activeTab === "profile" ? (
                <>
                  <div className="text-xl font-semibold">Profile Settings</div>

                  <div className="mt-6">
                    <div className="text-sm text-white/70">Display Name</div>
                    <input
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Enter your name"
                      className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
                    />
                  </div>

                  <div className="mt-6">
                    <div className="text-sm text-white/70">Email Address</div>
                    <input
                      value={meLoading ? "…" : me?.email || ""}
                      disabled
                      className="mt-2 h-12 w-full cursor-not-allowed rounded-xl border border-white/10 bg-black/10 px-4 text-sm text-white/70 outline-none"
                    />
                    <div className="mt-2 text-xs text-white/40">Email cannot be changed</div>
                  </div>

                  <button
                    type="button"
                    onClick={saveProfile}
                    disabled={savingProfile}
                    className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-60"
                  >
                    <span aria-hidden>💾</span>
                    {savingProfile ? "Saving…" : "Save Changes"}
                  </button>
                </>
              ) : null}

              {activeTab === "notifications" ? (
                <>
                  <div className="text-xl font-semibold">Notifications</div>
                  <div className="mt-2 text-sm text-white/60">
                    (UI only for now) Hook these to your backend later if you want stored preferences.
                  </div>

                  <div className="mt-6 space-y-3">
                    <label className="flex items-center justify-between rounded-xl border border-white/10 bg-black/10 px-4 py-3">
                      <span className="text-sm text-white/80">Product updates</span>
                      <input type="checkbox" className="h-4 w-4" defaultChecked />
                    </label>

                    <label className="flex items-center justify-between rounded-xl border border-white/10 bg-black/10 px-4 py-3">
                      <span className="text-sm text-white/80">Security alerts</span>
                      <input type="checkbox" className="h-4 w-4" defaultChecked />
                    </label>

                    <label className="flex items-center justify-between rounded-xl border border-white/10 bg-black/10 px-4 py-3">
                      <span className="text-sm text-white/80">Marketing</span>
                      <input type="checkbox" className="h-4 w-4" />
                    </label>
                  </div>

                  <button
                    type="button"
                    onClick={() => setOk("Saved (UI only).")}
                    className="mt-6 rounded-xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-500"
                  >
                    Save Changes
                  </button>
                </>
              ) : null}

              {activeTab === "appearance" ? (
                <>
                  <div className="text-xl font-semibold">Appearance</div>
                  <div className="mt-2 text-sm text-white/60">(UI only for now) Keep your default dark theme.</div>

                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => setOk("Dark selected (UI only).")}
                      className="rounded-xl border border-white/10 bg-black/10 px-4 py-4 text-left hover:bg-white/5"
                    >
                      <div className="text-sm font-semibold">Dark</div>
                      <div className="mt-1 text-xs text-white/50">Recommended</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setOk("Light selected (UI only).")}
                      className="rounded-xl border border-white/10 bg-black/10 px-4 py-4 text-left hover:bg-white/5"
                    >
                      <div className="text-sm font-semibold">Light</div>
                      <div className="mt-1 text-xs text-white/50">Optional</div>
                    </button>
                  </div>
                </>
              ) : null}

              {activeTab === "security" ? (
                <>
                  <div className="text-xl font-semibold">Security</div>

                  {/* change password */}
                  <div className="mt-6 rounded-2xl border border-white/10 bg-black/10 p-5">
                    <div className="text-base font-semibold">Change password</div>
                    <div className="mt-1 text-sm text-white/60">
                      If your account is OAuth-only, the backend will block “current password” changes — that’s expected.
                    </div>

                    <input
                      value={curPw}
                      onChange={(e) => setCurPw(e.target.value)}
                      type="password"
                      placeholder="Current password"
                      className="mt-4 h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
                    />
                    <input
                      value={newPw}
                      onChange={(e) => setNewPw(e.target.value)}
                      type="password"
                      placeholder="New password (min 8 chars)"
                      className="mt-3 h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
                    />

                    <button
                      type="button"
                      onClick={changePassword}
                      disabled={savingPw}
                      className="mt-4 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-60"
                    >
                      {savingPw ? "Saving…" : "Update password"}
                    </button>
                  </div>

                  {/* BYOK */}
                  <div className="mt-6 rounded-2xl border border-white/10 bg-black/10 p-5">
                    <div className="text-base font-semibold">Bring your own key (BYOK)</div>
                    <div className="mt-1 text-sm text-white/60">
                      Backend allows BYOK for admin or paid tiers (basic/pro/elite). If ineligible you’ll get 403.
                    </div>

                    <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4">
                      <div className="text-sm text-white/70">Current status</div>
                      <div className="mt-1 text-base font-semibold">
                        {byokLoading ? "…" : byokStatus?.has_key ? "Key on file" : "No key saved"}
                      </div>
                      <div className="mt-2 text-xs text-white/50">
                        Provider: <span className="text-white/70">{byokStatus?.provider || "—"}</span>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div>
                        <select
                          value={provider}
                          onChange={(e) => setProvider(e.target.value)}
                          className="h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white outline-none focus:border-blue-400/40"
                        >
                          <option value="openai">openai</option>
                          <option value="anthropic">anthropic</option>
                          <option value="gemini">gemini</option>
                          <option value="replicate">replicate</option>
                          <option value="grok">grok</option>
                        </select>

                        <input
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          placeholder="Paste API key…"
                          className="mt-3 h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
                        />

                        <button
                          type="button"
                          onClick={saveKey}
                          disabled={!canSaveKey}
                          className="mt-3 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
                        >
                          {savingKey ? "Saving…" : "Save key"}
                        </button>
                      </div>

                      <div>
                        <button
                          type="button"
                          onClick={deleteKey}
                          disabled={deletingKey || !byokStatus?.has_key}
                          className="h-11 w-full rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-white hover:bg-white/10 disabled:opacity-60"
                        >
                          {deletingKey ? "Deleting…" : "Delete key"}
                        </button>

                        <button
                          type="button"
                          onClick={loadByok}
                          className="mt-3 h-11 w-full rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-white hover:bg-white/10"
                        >
                          Refresh status
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
