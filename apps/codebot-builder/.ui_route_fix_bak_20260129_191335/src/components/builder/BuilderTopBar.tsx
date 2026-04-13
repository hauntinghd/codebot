"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

type DeviceMode = "desktop" | "tablet" | "mobile";
type ViewMode = "preview" | "code";

type Props = {
  projectName: string;
  onProjectRename: (name: string) => void;
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  device: DeviceMode;
  onDeviceChange: (d: DeviceMode) => void;

  projectId?: string;
  onNewProject?: () => void;
  onShareProject?: () => void | Promise<void>;
  onExportProject?: () => void;
};

const BASE = "/codebot";

export default function BuilderTopBar(props: Props) {
  const {
    projectName,
    onProjectRename,
    view,
    onViewChange,
    device,
    onDeviceChange,
    projectId,
    onNewProject,
    onShareProject,
    onExportProject,
  } = props;

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const deviceLabel = useMemo(() => {
    if (device === "mobile") return "Mobile";
    if (device === "tablet") return "Tablet";
    return "Desktop";
  }, [device]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  function go(path: string) {
    setMenuOpen(false);
    window.location.assign(`${BASE}${path.startsWith("/") ? path : `/${path}`}`);
  }

  async function logout() {
    setMenuOpen(false);
    try {
      await fetch(`${BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
    } catch {
      // ignore
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("codebot_access_token");
    localStorage.removeItem("cb_access_token");
    window.location.assign(`${BASE}/login`);
  }

  async function openStripePortal() {
    setMenuOpen(false);

    // Portal is confirmed working: GET /api/billing/portal -> {url}
    try {
      const res = await fetch(`${BASE}/api/billing/portal`, {
        method: "GET",
        credentials: "include",
        headers: { accept: "application/json" },
        cache: "no-store",
      });
      const ct = res.headers.get("content-type") || "";
      if (res.ok && ct.includes("application/json")) {
        const data = await res.json().catch(() => ({}));
        const url = String((data as any)?.url || "").trim();
        if (url) {
          window.location.assign(url);
          return;
        }
      }
    } catch {
      // ignore
    }

    // fallback route
    go("/account/upgrade");
  }

  function rename() {
    const n = window.prompt("Rename project", (projectName || "").trim() || "Untitled Project");
    if (n?.trim()) onProjectRename(n.trim());
  }

  return (
    <header className="cb-topbar" role="banner">
      {/* LEFT */}
      <div className="cb-topbar__left">
        <div
          className="h-9 w-9 rounded-xl bg-sky-500/20 border border-sky-400/30 inline-flex items-center justify-center shrink-0 cursor-pointer"
          onClick={() => go("/dashboard")}
          role="button"
          tabIndex={0}
          title="Dashboard"
        >
          <span className="text-sky-200 font-semibold leading-none">✦</span>
        </div>

        <div className="min-w-0">
          <div className="text-white font-semibold leading-none">CodeBot™</div>
          <div className="text-[11px] text-white/45 leading-none mt-1">
            Builder • {deviceLabel} • {view === "preview" ? "Preview" : "Code"}
          </div>
        </div>

        <button
          type="button"
          className={[
            "h-9 max-w-[340px] px-3 rounded-xl",
            "bg-white/5 border border-white/10",
            "text-white/90 text-sm inline-flex items-center gap-2",
            "truncate hover:bg-white/8 leading-none",
          ].join(" ")}
          title={projectId ? `Project: ${projectId}` : "Rename project"}
          onClick={rename}
        >
          <span className="truncate">{(projectName || "Untitled Project").trim() || "Untitled Project"}</span>
          <span className="text-white/50 leading-none">▾</span>
        </button>

        {/* Quick actions */}
        <div className="flex items-center gap-2">
          {onNewProject ? (
            <button className="cb-btn" type="button" onClick={onNewProject}>
              New
            </button>
          ) : null}
          {onShareProject ? (
            <button className="cb-btn" type="button" onClick={() => void onShareProject()}>
              Share
            </button>
          ) : null}
          {onExportProject ? (
            <button className="cb-btn" type="button" onClick={onExportProject}>
              Export
            </button>
          ) : null}
        </div>
      </div>

      {/* CENTER */}
      <div className="cb-topbar__center">
        <div className="h-9 px-1 rounded-xl bg-white/5 border border-white/10 inline-flex items-center gap-1">
          <button
            type="button"
            onClick={() => onViewChange("preview")}
            className={[
              "h-7 px-3 rounded-lg text-sm font-semibold",
              view === "preview" ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5",
            ].join(" ")}
          >
            Preview
          </button>
          <button
            type="button"
            onClick={() => onViewChange("code")}
            className={[
              "h-7 px-3 rounded-lg text-sm font-semibold",
              view === "code" ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5",
            ].join(" ")}
          >
            Code
          </button>
        </div>

        <div className="h-9 px-2 rounded-xl bg-white/5 border border-white/10 inline-flex items-center gap-1">
          <button
            type="button"
            className={[
              "h-7 w-8 rounded-lg border border-white/10",
              device === "desktop" ? "bg-white/10" : "bg-transparent hover:bg-white/5",
            ].join(" ")}
            onClick={() => onDeviceChange("desktop")}
            title="Desktop"
          >
            ▢
          </button>
          <button
            type="button"
            className={[
              "h-7 w-8 rounded-lg border border-white/10",
              device === "tablet" ? "bg-white/10" : "bg-transparent hover:bg-white/5",
            ].join(" ")}
            onClick={() => onDeviceChange("tablet")}
            title="Tablet"
          >
            ▭
          </button>
          <button
            type="button"
            className={[
              "h-7 w-8 rounded-lg border border-white/10",
              device === "mobile" ? "bg-white/10" : "bg-transparent hover:bg-white/5",
            ].join(" ")}
            onClick={() => onDeviceChange("mobile")}
            title="Mobile"
          >
            ▯
          </button>

          <span className="text-xs text-white/55 font-semibold px-2">{deviceLabel}</span>
        </div>
      </div>

      {/* RIGHT */}
      <div className="cb-topbar__right">
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            className="h-9 w-9 rounded-xl border border-white/10 bg-white/5 hover:bg-white/8 inline-flex items-center justify-center"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((s) => !s)}
            title="Account"
          >
            ☰
          </button>

          {menuOpen ? (
            <div className="cb-menu cb-menu--right" role="menu" aria-label="Account menu">
              <button className="cb-menuitem" type="button" role="menuitem" onClick={() => go("/dashboard")}>
                Dashboard
              </button>
              <button className="cb-menuitem" type="button" role="menuitem" onClick={() => go("/account")}>
                Account
              </button>
              <button className="cb-menuitem" type="button" role="menuitem" onClick={() => go("/settings")}>
                Settings
              </button>
              <button className="cb-menuitem" type="button" role="menuitem" onClick={() => go("/account/upgrade")}>
                Upgrade / Credits
              </button>
              <button className="cb-menuitem" type="button" role="menuitem" onClick={openStripePortal}>
                Open Stripe Portal
              </button>

              <div className="cb-menusep" />

              <button className="cb-menuitem" type="button" role="menuitem" onClick={() => go("/terms")}>
                Terms of service
              </button>

              <div className="cb-menusep" />

              <button className="cb-menuitem danger" type="button" role="menuitem" onClick={logout}>
                Log out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
