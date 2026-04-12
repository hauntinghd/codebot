"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, apiFetchRaw, clearTokens } from "../lib/api";

const LOGIN_URL = "/login";

// PATHS only
const ME_PATH = "/me";
const ARCH_PROJECTS_PATH = "/architecture/projects";

type MeOut = {
  id: string;
  email: string;
  is_admin: boolean;
  subscription_status?: string;
  plan?: string;
  current_period_end?: number;
  credits_remaining?: number | null;
};

type ArchitectureProject = {
  id: string;
  name: string;
  description?: string | null;
  created_at?: number | string | null;
  updated_at?: number | string | null;
};

async function jsonOrNull<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function normalizeProjects(payload: any): ArchitectureProject[] {
  const arr =
    (Array.isArray(payload) && payload) ||
    (Array.isArray(payload?.projects) && payload.projects) ||
    (Array.isArray(payload?.items) && payload.items) ||
    [];

  return arr
    .filter(Boolean)
    .map((p: any) => ({
      id: String(p.id ?? ""),
      name: String(p.name ?? ""),
      description: p.description ?? null,
      created_at: p.created_at ?? null,
      updated_at: p.updated_at ?? null,
    }))
    .filter((p: ArchitectureProject) => p.id && p.name);
}

function initials(email?: string) {
  const e = (email || "").trim();
  if (!e) return "?";
  const left = e.split("@")[0] || e;
  const parts = left.split(/[._-]+/).filter(Boolean);
  const a = (parts[0]?.[0] || left[0] || "?").toUpperCase();
  const b = (parts[1]?.[0] || "").toUpperCase();
  return (a + b).slice(0, 2);
}

export default function DashboardClient() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [me, setMe] = useState<MeOut | null>(null);
  const [projects, setProjects] = useState<ArchitectureProject[]>([]);

  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  const [error, setError] = useState<string | null>(null);

  // profile dropdown
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocDown(e: MouseEvent) {
      if (!menuRef.current) return;
      if (!menuOpen) return;
      if (!menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onDocDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const canCreate = useMemo(
    () => name.trim().length >= 2 && !creating,
    [name, creating]
  );

  async function requireAuthedMe(): Promise<MeOut | null> {
    const res = await apiFetchRaw(ME_PATH, { method: "GET", auth: true });

    if (res.status === 401) {
      clearTokens();
      window.location.assign(LOGIN_URL);
      return null;
    }

    if (!res.ok) {
      const t = await res.text().catch(() => "");
      setError(`Failed to load user (HTTP ${res.status}). ${t || ""}`.trim());
      return null;
    }

    return await jsonOrNull<MeOut>(res);
  }

  async function loadProjects(): Promise<void> {
    const res = await apiFetchRaw(ARCH_PROJECTS_PATH, {
      method: "GET",
      auth: true,
    });

    if (res.status === 401) {
      clearTokens();
      window.location.assign(LOGIN_URL);
      return;
    }

    if (!res.ok) {
      const t = await res.text().catch(() => "");
      setError(`Failed to load projects (HTTP ${res.status}). ${t || ""}`.trim());
      setProjects([]);
      return;
    }

    const payload = await jsonOrNull<any>(res);
    setProjects(normalizeProjects(payload));
  }

  async function loadAll(): Promise<void> {
    setError(null);

    const m = await requireAuthedMe();
    if (!m) return;
    setMe(m);

    await loadProjects();
  }

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        await loadAll();
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } finally {
      setRefreshing(false);
    }
  }

  async function onLogout() {
    clearTokens();
    window.location.assign(LOGIN_URL);
  }

  async function onCreate() {
    const nm = name.trim();
    const description = desc.trim() || null;
    if (nm.length < 2) return;

    setCreating(true);
    setError(null);

    try {
      const res = await apiFetchRaw(ARCH_PROJECTS_PATH, {
        method: "POST",
        auth: true,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: nm, description }),
      });

      if (res.status === 401) {
        clearTokens();
        window.location.assign(LOGIN_URL);
        return;
      }

      if (!res.ok) {
        const t = await res.text().catch(() => "");
        setError(`Create failed (HTTP ${res.status}). ${t || ""}`.trim());
        return;
      }

      const payload = await jsonOrNull<any>(res);
      const newId = String(
        payload?.id ?? payload?.project_id ?? payload?.project?.id ?? ""
      ).trim();

      setName("");
      setDesc("");

      await loadProjects();

      if (newId) {
        window.location.assign(`/codebot/project/${encodeURIComponent(newId)}`);
      }
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0f16] text-white">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-3xl font-semibold tracking-tight">Dashboard</div>
            <div className="mt-1 text-sm text-white/60">
              Create a project, then open it to generate plans and deploy.
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing || loading}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10 disabled:opacity-60"
            >
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>

            {/* Profile dropdown */}
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10 flex items-center gap-2"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                title={me?.email || ""}
              >
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-black/20 text-xs font-black">
                  {initials(me?.email)}
                </span>
                <span className="hidden sm:inline max-w-[150px] truncate font-semibold text-white/80">
                  {me?.email || "Profile"}
                </span>
                <span className="text-white/60">▾</span>
              </button>

              {menuOpen ? (
                <div
                  className="absolute right-0 mt-2 w-64 rounded-2xl border border-white/10 bg-[#0b0f16]/95 p-2 shadow-xl backdrop-blur"
                  role="menu"
                >
                  <div className="px-3 py-2">
                    <div className="text-xs font-extrabold uppercase tracking-wide text-white/50">
                      Signed in
                    </div>
                    <div className="mt-1 text-sm font-black text-white truncate">
                      {me?.email || "—"}
                    </div>
                    <div className="mt-1 text-xs text-white/50">
                      {me?.is_admin ? "Admin" : "User"}
                    </div>
                  </div>

                  <div className="my-2 h-px bg-white/10" />

                  <button
                    className="w-full rounded-xl px-3 py-2 text-left text-sm font-bold text-white/80 hover:bg-white/5"
                    onClick={() => {
                      setMenuOpen(false);
                      window.location.assign("/codebot/account");
                    }}
                    role="menuitem"
                  >
                    Account
                  </button>
                  <button
                    className="w-full rounded-xl px-3 py-2 text-left text-sm font-bold text-white/80 hover:bg-white/5"
                    onClick={() => {
                      setMenuOpen(false);
                      window.location.assign("/codebot/settings");
                    }}
                    role="menuitem"
                  >
                    Settings
                  </button>
                  <button
                    className="w-full rounded-xl px-3 py-2 text-left text-sm font-bold text-white/80 hover:bg-white/5"
                    onClick={() => {
                      setMenuOpen(false);
                      window.location.assign("/codebot/account/upgrade");
                    }}
                    role="menuitem"
                  >
                    Upgrade / Billing
                  </button>

                  <div className="my-2 h-px bg-white/10" />

                  <button
                    type="button"
                    onClick={onLogout}
                    className="w-full rounded-xl px-3 py-2 text-left text-sm font-black text-red-200 hover:bg-red-500/10"
                    role="menuitem"
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-white/80">
              Signed in as{" "}
              <span className="font-semibold text-white">{me?.email || "—"}</span>
              {me?.is_admin ? (
                <span className="ml-2 rounded bg-blue-500/20 px-2 py-0.5 text-xs text-blue-100">
                  Admin
                </span>
              ) : null}
            </div>

            <div className="text-xs text-white/60">
              API: <span className="text-white/80">{API_BASE}</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="text-base font-semibold">Create Project</div>
          <div className="mt-1 text-sm text-white/60">
            This creates an architecture project (name + description).
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Project name"
              className="h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
            />
            <textarea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="Short description (optional)"
              rows={3}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-white/35 outline-none focus:border-blue-400/40"
            />
          </div>

          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={onCreate}
              disabled={!canCreate}
              className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
            >
              {creating ? "Creating…" : "Create Project"}
            </button>

            <button
              type="button"
              onClick={() => {
                setName("");
                setDesc("");
              }}
              disabled={creating}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm hover:bg-white/10 disabled:opacity-60"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="text-base font-semibold">Your Projects</div>
            <div className="text-sm text-white/60">
              {loading ? "…" : `${projects.length} total`}
            </div>
          </div>

          <div className="mt-4">
            {loading ? (
              <div className="text-sm text-white/60">Loading…</div>
            ) : projects.length === 0 ? (
              <div className="text-sm text-white/60">No projects yet.</div>
            ) : (
              <div className="space-y-3">
                {projects.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-xl border border-white/10 bg-black/20 px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold">{p.name}</div>
                        {p.description ? (
                          <div className="mt-1 text-xs text-white/60">
                            {p.description}
                          </div>
                        ) : (
                          <div className="mt-1 text-xs text-white/40">
                            No description
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
                          onClick={() =>
                            window.location.assign(
                              `/codebot/project/${encodeURIComponent(p.id)}`
                            )
                          }
                        >
                          Open
                        </button>
                      </div>
                    </div>

                    <div className="mt-2 text-[11px] text-white/35 break-all">
                      {p.id}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => window.location.assign("/codebot/")}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
          >
            Home
          </button>
          <button
            type="button"
            onClick={() => window.location.assign("/project")}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
          >
            Project
          </button>
        </div>
      </div>
    </div>
  );
}
