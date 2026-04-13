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
  onExportProjectAsZip?: () => void;
  onSaveProject?: () => void;
  onOpenProject?: () => void;
  onDeploy?: (target: "vm" | "vercel" | "netlify", customDomain?: string) => void;
};

const BASE = "/codebot";

const S = {
  bar: {
    height: 56,
    padding: "0 16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    borderBottom: "1px solid rgba(255,255,255,0.04)",
    background: "linear-gradient(180deg, rgba(255,255,255,0.02) 0%, transparent 100%)",
  } as React.CSSProperties,
  left: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    minWidth: 0,
    flex: "1 1 0",
  } as React.CSSProperties,
  center: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    justifyContent: "center",
  } as React.CSSProperties,
  right: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    justifyContent: "flex-end",
    flex: "1 1 0",
  } as React.CSSProperties,
  logo: {
    width: 34,
    height: 34,
    borderRadius: "50%",
    cursor: "pointer",
    flexShrink: 0,
  } as React.CSSProperties,
  brandWrap: { minWidth: 0 } as React.CSSProperties,
  brandName: {
    fontSize: 14,
    fontWeight: 600,
    color: "white",
    lineHeight: 1,
  } as React.CSSProperties,
  brandSub: {
    fontSize: 11,
    color: "rgba(255,255,255,0.45)",
    lineHeight: 1,
    marginTop: 3,
  } as React.CSSProperties,
  projBtn: {
    height: 36,
    maxWidth: 260,
    padding: "0 12px",
    borderRadius: 8,
    border: "none",
    background: "rgba(255,255,255,0.06)",
    color: "rgba(255,255,255,0.85)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    overflow: "hidden",
    whiteSpace: "nowrap" as const,
    textOverflow: "ellipsis",
    position: "relative" as const,
  } as React.CSSProperties,
  seg: {
    height: 36,
    padding: "0 4px",
    borderRadius: 10,
    background: "rgba(255,255,255,0.04)",
    display: "inline-flex",
    alignItems: "center",
    gap: 2,
  } as React.CSSProperties,
  segBtn: (active: boolean) => ({
    height: 28,
    padding: "0 14px",
    borderRadius: 7,
    border: "none",
    background: active ? "rgba(255,255,255,0.1)" : "transparent",
    color: active ? "white" : "rgba(255,255,255,0.6)",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  }) as React.CSSProperties,
  devBtn: (active: boolean) => ({
    height: 28,
    padding: "0 10px",
    borderRadius: 7,
    border: "none",
    background: active ? "rgba(255,255,255,0.1)" : "transparent",
    color: active ? "white" : "rgba(255,255,255,0.55)",
    fontSize: 12,
    fontWeight: 500,
    cursor: "pointer",
  }) as React.CSSProperties,
  menuBtn: {
    width: 36,
    height: 36,
    borderRadius: 8,
    border: "none",
    background: "rgba(255,255,255,0.06)",
    color: "rgba(255,255,255,0.8)",
    fontSize: 16,
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
  } as React.CSSProperties,
  drop: {
    position: "absolute" as const,
    top: "calc(100% + 8px)",
    left: 0,
    width: 220,
    borderRadius: 12,
    background: "rgba(15,20,25,0.98)",
    backdropFilter: "blur(20px)",
    boxShadow: "0 24px 48px -12px rgba(0,0,0,0.6)",
    overflow: "hidden",
    zIndex: 9999,
    padding: 6,
  } as React.CSSProperties,
  dropRight: {
    position: "absolute" as const,
    top: "calc(100% + 8px)",
    right: 0,
    width: 220,
    borderRadius: 12,
    background: "rgba(15,20,25,0.98)",
    backdropFilter: "blur(20px)",
    boxShadow: "0 24px 48px -12px rgba(0,0,0,0.6)",
    overflow: "hidden",
    zIndex: 9999,
    padding: 6,
  } as React.CSSProperties,
  dropItem: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 8,
    border: "none",
    background: "transparent",
    color: "rgba(255,255,255,0.8)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    textAlign: "left" as const,
    display: "flex",
    alignItems: "center",
    gap: 10,
  } as React.CSSProperties,
  dropIcon: {
    width: 16,
    height: 16,
    opacity: 0.55,
    flexShrink: 0,
  } as React.CSSProperties,
  dropSep: {
    height: 1,
    background: "rgba(255,255,255,0.06)",
    margin: "4px 8px",
  } as React.CSSProperties,
  projLabel: {
    padding: "8px 12px 6px",
    fontSize: 11,
    fontWeight: 600,
    color: "rgba(255,255,255,0.35)",
    letterSpacing: "0.04em",
    textTransform: "uppercase" as const,
  } as React.CSSProperties,
};

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
    onExportProjectAsZip,
    onSaveProject,
    onOpenProject,
    onDeploy,
  } = props;

  const [menuOpen, setMenuOpen] = useState(false);
  const [projOpen, setProjOpen] = useState(false);
  const [deployOpen, setDeployOpen] = useState(false);
  const [customDomain, setCustomDomain] = useState("");
  const menuRef = useRef<HTMLDivElement | null>(null);
  const projRef = useRef<HTMLDivElement | null>(null);
  const deployRef = useRef<HTMLDivElement | null>(null);

  const deviceLabel = useMemo(() => {
    if (device === "mobile") return "Mobile";
    if (device === "tablet") return "Tablet";
    return "Desktop";
  }, [device]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
      if (!projRef.current?.contains(e.target as Node)) setProjOpen(false);
      if (!deployRef.current?.contains(e.target as Node)) setDeployOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setMenuOpen(false); setProjOpen(false); setDeployOpen(false); }
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
    setProjOpen(false);
    window.location.assign(`${BASE}${path.startsWith("/") ? path : `/${path}`}`);
  }

  async function logout() {
    setMenuOpen(false);
    try {
      await fetch(`${BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
    } catch {}
    localStorage.removeItem("access_token");
    localStorage.removeItem("codebot_access_token");
    localStorage.removeItem("cb_access_token");
    window.location.assign(`${BASE}/login`);
  }

  async function openStripePortal() {
    setMenuOpen(false);
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
        if (url) { window.location.assign(url); return; }
      }
    } catch {}
    go("/account/upgrade");
  }

  function rename() {
    setProjOpen(false);
    const n = window.prompt("Rename project", (projectName || "").trim() || "Untitled Project");
    if (n?.trim()) onProjectRename(n.trim());
  }

  const accountItems = [
    { label: "Dashboard", action: () => go("/dashboard") },
    { label: "Account", action: () => go("/account") },
    { label: "Settings", action: () => go("/settings") },
    { label: "Upgrade / Credits", action: () => go("/account/upgrade") },
    { label: "Stripe Portal", action: openStripePortal },
    null,
    { label: "Terms of Service", action: () => go("/terms") },
    null,
    { label: "Log out", action: logout, danger: true },
  ];

  return (
    <header style={S.bar} role="banner">
      {/* LEFT */}
      <div style={S.left}>
        <img
          src={`${BASE}/logo.png`}
          alt="NYPTID"
          width={34}
          height={34}
          style={S.logo}
          onClick={() => go("/dashboard")}
          role="button"
          tabIndex={0}
          title="Dashboard"
        />

        <div style={S.brandWrap}>
          <div style={S.brandName}>CodeBot™</div>
          <div style={S.brandSub}>Builder • {deviceLabel} • {view === "preview" ? "Preview" : "Code"}</div>
        </div>

        {/* Project dropdown */}
        <div ref={projRef} style={{ position: "relative" }}>
          <button
            type="button"
            style={S.projBtn}
            onClick={() => setProjOpen((s) => !s)}
            title={projectId ? `Project: ${projectId}` : "Project actions"}
            aria-haspopup="menu"
            aria-expanded={projOpen}
          >
            <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
              {(projectName || "Untitled Project").trim() || "Untitled Project"}
            </span>
            <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 10 }}>▾</span>
          </button>

          {projOpen ? (
            <div style={S.drop} role="menu" aria-label="Project actions">
              {projectId ? (
                <div style={S.projLabel}>{projectId.slice(0, 12)}</div>
              ) : null}

              <button type="button" role="menuitem" style={S.dropItem} onClick={rename}>
                <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                </svg>
                Rename
              </button>

              {onNewProject ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); onNewProject(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                  New Project
                </button>
              ) : null}

              <div style={S.dropSep} />

              {onShareProject ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); void onShareProject(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                  </svg>
                  Share
                </button>
              ) : null}

              {onExportProject ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); onExportProject(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Export JSON
                </button>
              ) : null}
              {onExportProjectAsZip ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); onExportProjectAsZip(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Export as ZIP
                </button>
              ) : null}
              {onSaveProject ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); onSaveProject(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" />
                  </svg>
                  Save project
                </button>
              ) : null}
              {onOpenProject ? (
                <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setProjOpen(false); onOpenProject(); }}>
                  <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  </svg>
                  Open project
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {/* CENTER */}
      <div style={S.center}>
        <div style={S.seg}>
          <button type="button" style={S.segBtn(view === "preview")} onClick={() => onViewChange("preview")}>Preview</button>
          <button type="button" style={S.segBtn(view === "code")} onClick={() => onViewChange("code")}>Code</button>
        </div>

        <div style={S.seg}>
          <button type="button" style={S.devBtn(device === "desktop")} onClick={() => onDeviceChange("desktop")} title="Desktop">Desktop</button>
          <button type="button" style={S.devBtn(device === "tablet")} onClick={() => onDeviceChange("tablet")} title="Tablet">Tablet</button>
          <button type="button" style={S.devBtn(device === "mobile")} onClick={() => onDeviceChange("mobile")} title="Mobile">Mobile</button>
        </div>
      </div>

      {/* RIGHT */}
      <div style={S.right}>
        {/* Deploy dropdown */}
        <div style={{ position: "relative" }} ref={deployRef}>
          <button
            type="button"
            style={{ ...S.menuBtn, width: "auto", padding: "0 12px", gap: 6, display: "inline-flex", alignItems: "center", fontSize: 13, fontWeight: 600, background: "rgba(34,197,94,0.15)", color: "rgba(134,239,172,1)" }}
            aria-haspopup="menu"
            aria-expanded={deployOpen}
            onClick={() => setDeployOpen((s) => !s)}
            title="Deploy project"
          >
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5Z" /><path d="m2 17 10 5 10-5" /><path d="m2 12 10 5 10-5" /></svg>
            Deploy
            <span style={{ fontSize: 10, opacity: 0.6 }}>▾</span>
          </button>

          {deployOpen ? (
            <div style={S.dropRight} role="menu" aria-label="Deploy options">
              <div style={{ padding: "8px 12px 6px", fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.35)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                Deploy to
              </div>
              <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setDeployOpen(false); onDeploy?.("netlify", customDomain || undefined); }}>
                <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 19.5h20L12 2z" /><path d="M12 2v17.5" />
                </svg>
                Netlify
              </button>
              <button type="button" role="menuitem" style={S.dropItem} onClick={() => { setDeployOpen(false); onDeploy?.("vercel", customDomain || undefined); }}>
                <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2l10 18H2L12 2z" />
                </svg>
                Vercel
              </button>
              <button type="button" role="menuitem" style={{...S.dropItem, opacity: 0.4, cursor: "default"}} disabled>
                <svg style={S.dropIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect x="2" y="14" width="20" height="8" rx="2" ry="2" /><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
                NYPTID Server — Coming Soon
              </button>
              <div style={{ padding: "6px 12px 8px", borderTop: "1px solid rgba(255,255,255,0.06)", marginTop: 4 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Custom Domain (optional)</div>
                <input
                  type="text"
                  placeholder="e.g. mysite.com"
                  value={customDomain}
                  onChange={(e) => setCustomDomain(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  style={{ width: "100%", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "5px 8px", fontSize: 12, color: "rgba(255,255,255,0.85)", outline: "none", boxSizing: "border-box" }}
                />
              </div>
            </div>
          ) : null}
        </div>

        <div style={{ position: "relative" }} ref={menuRef}>
          <button
            type="button"
            style={S.menuBtn}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((s) => !s)}
            title="Menu"
          >
            ☰
          </button>

          {menuOpen ? (
            <div style={S.dropRight} role="menu" aria-label="Account menu">
              {accountItems.map((item, i) =>
                item === null ? (
                  <div key={`sep-${i}`} style={S.dropSep} />
                ) : (
                  <button
                    key={item.label}
                    type="button"
                    role="menuitem"
                    style={{
                      ...S.dropItem,
                      color: (item as any).danger ? "rgba(255,120,120,0.9)" : S.dropItem.color,
                    }}
                    onClick={item.action}
                  >
                    {item.label}
                  </button>
                )
              )}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
