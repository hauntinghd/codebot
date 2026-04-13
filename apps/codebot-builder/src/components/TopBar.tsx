"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

type Mode = "preview" | "code";
type Device = "desktop" | "tablet" | "mobile";
type DeployTarget = "vercel" | "netlify" | "my_server";

type Props = {
  mode: Mode;
  device: Device;
  projectName: string;

  onModeChange: (m: Mode) => void;
  onDeviceChange: (d: Device) => void;

  onNewProject: () => void;
  onOpenRecent: () => void;

  onShare: () => void;
  onExport: () => void;

  onDeploy: (target: DeployTarget) => void;

  onProfileBilling: () => void;
  onProfileLogout: () => void;
};

function useOutsideClick(
  ref: React.RefObject<HTMLElement | null>,
  open: boolean,
  onClose: () => void
) {
  useEffect(() => {
    if (!open) return;

    function onDown(e: MouseEvent) {
      const el = ref.current;
      if (!el) return;
      if (el.contains(e.target as Node)) return;
      onClose();
    }

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }

    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, ref]);
}

function IconPill({
  children,
  active,
}: {
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <span
      className={[
        "h-9 w-9 rounded-xl border inline-flex items-center justify-center",
        "leading-none select-none",
        active
          ? "bg-white/10 border-white/20"
          : "bg-white/5 border-white/10 hover:bg-white/8",
      ].join(" ")}
    >
      {children}
    </span>
  );
}

function MenuItem({
  label,
  sub,
  onClick,
  danger,
}: {
  label: string;
  sub?: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "w-full text-left px-3 py-2 rounded-lg",
        "inline-flex items-start gap-2",
        "hover:bg-white/5 focus:outline-none focus:bg-white/5",
        danger ? "text-rose-200" : "text-white/90",
      ].join(" ")}
    >
      <span className="flex-1">
        <span className="block text-sm font-semibold leading-snug">{label}</span>
        {sub ? (
          <span className="block text-xs text-white/50 leading-snug">{sub}</span>
        ) : null}
      </span>
    </button>
  );
}

function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="cb-modal__overlay" role="dialog" aria-modal="true">
      <div className="cb-modal__panel">
        <div className="cb-modal__header">
          <div className="cb-modal__title">{title}</div>
          <button
            type="button"
            className="cb-btn cb-btn--ghost"
            onClick={onClose}
            aria-label="Close"
            title="Close"
          >
            ✕
          </button>
        </div>
        <div className="cb-modal__body">{children}</div>
      </div>
    </div>
  );
}

export default function TopBar(props: Props) {
  const {
    mode,
    device,
    projectName,

    onModeChange,
    onDeviceChange,

    onNewProject,
    onOpenRecent,

    onShare,
    onExport,

    onDeploy,

    onProfileBilling,
    onProfileLogout,
  } = props;

  const [projOpen, setProjOpen] = useState(false);
  const [deployOpen, setDeployOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [projSettingsOpen, setProjSettingsOpen] = useState(false);

  const projRef = useRef<HTMLDivElement | null>(null);
  const deployRef = useRef<HTMLDivElement | null>(null);
  const profileRef = useRef<HTMLDivElement | null>(null);

  useOutsideClick(projRef, projOpen, () => setProjOpen(false));
  useOutsideClick(deployRef, deployOpen, () => setDeployOpen(false));
  useOutsideClick(profileRef, profileOpen, () => setProfileOpen(false));

  const title = useMemo(
    () => (projectName || "Untitled Project").trim() || "Untitled Project",
    [projectName]
  );

  return (
    <>
      <header className="cb-topbar" role="banner">
        {/* LEFT */}
        <div className="cb-topbar__left">
          <div className="h-9 w-9 rounded-xl bg-sky-500/20 border border-sky-400/30 inline-flex items-center justify-center shrink-0">
            <span className="text-sky-200 font-semibold leading-none">✦</span>
          </div>

          <div className="min-w-0">
            <div className="text-white font-semibold leading-none">CodeBot™</div>
            <div className="text-[11px] text-white/45 leading-none mt-1">
              Ready to build
            </div>
          </div>

          {/* Project dropdown */}
          <div className="relative min-w-0" ref={projRef}>
            <button
              type="button"
              onClick={() => setProjOpen((v) => !v)}
              className={[
                "h-9 max-w-[340px] px-3 rounded-xl",
                "bg-white/5 border border-white/10",
                "text-white/90 text-sm inline-flex items-center gap-2",
                "truncate hover:bg-white/8",
                "leading-none",
              ].join(" ")}
              title={title}
            >
              <span className="truncate">{title}</span>
              <span className="text-white/50 leading-none">▾</span>
            </button>

            {projOpen ? (
              <div className="cb-menu cb-menu--left">
                <div className="px-2 py-2 text-xs text-white/40">Project</div>

                <MenuItem
                  label="New project"
                  sub="Start from a blank project."
                  onClick={() => {
                    setProjOpen(false);
                    onNewProject();
                  }}
                />
                <MenuItem
                  label="Recent projects"
                  sub="Open a previously saved project."
                  onClick={() => {
                    setProjOpen(false);
                    onOpenRecent();
                  }}
                />

                <div className="my-2 h-px bg-white/10" />

                <MenuItem
                  label="Project settings"
                  sub="Share, export, and project configuration."
                  onClick={() => {
                    setProjOpen(false);
                    setProjSettingsOpen(true);
                  }}
                />
              </div>
            ) : null}
          </div>
        </div>

        {/* CENTER */}
        <div className="cb-topbar__center">
          <div className="h-9 px-1 rounded-xl bg-white/5 border border-white/10 inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => onModeChange("preview")}
              className={[
                "h-7 px-3 rounded-lg text-sm font-semibold",
                "leading-none inline-flex items-center justify-center",
                mode === "preview"
                  ? "bg-white/10 text-white"
                  : "text-white/70 hover:bg-white/5",
              ].join(" ")}
            >
              Preview
            </button>
            <button
              type="button"
              onClick={() => onModeChange("code")}
              className={[
                "h-7 px-3 rounded-lg text-sm font-semibold",
                "leading-none inline-flex items-center justify-center",
                mode === "code"
                  ? "bg-white/10 text-white"
                  : "text-white/70 hover:bg-white/5",
              ].join(" ")}
            >
              &lt;/&gt; <span className="ml-1">Code</span>
            </button>
          </div>

          <div className="inline-flex items-center gap-2">
            <button
              type="button"
              onClick={() => onDeviceChange("desktop")}
              aria-label="Desktop"
              title="Desktop"
            >
              <IconPill active={device === "desktop"}>
                <span className="text-[15px] leading-none">🖥️</span>
              </IconPill>
            </button>
            <button
              type="button"
              onClick={() => onDeviceChange("tablet")}
              aria-label="Tablet"
              title="Tablet"
            >
              <IconPill active={device === "tablet"}>
                <span className="text-[15px] leading-none">📱</span>
              </IconPill>
            </button>
            <button
              type="button"
              onClick={() => onDeviceChange("mobile")}
              aria-label="Mobile"
              title="Mobile"
            >
              <IconPill active={device === "mobile"}>
                <span className="text-[15px] leading-none">📳</span>
              </IconPill>
            </button>
          </div>
        </div>

        {/* RIGHT */}
        <div className="cb-topbar__right">
          {/* Deploy dropdown */}
          <div className="relative" ref={deployRef}>
            <button
              type="button"
              onClick={() => setDeployOpen((v) => !v)}
              className={[
                "h-9 px-4 rounded-xl border border-white/10",
                "inline-flex items-center justify-center gap-2",
                "bg-white/10 hover:bg-white/15",
                "text-white text-sm font-semibold leading-none",
              ].join(" ")}
              title="Deploy"
            >
              Deploy <span className="text-white/60">▾</span>
            </button>

            {deployOpen ? (
              <div className="cb-menu cb-menu--right">
                <div className="px-2 py-2 text-xs text-white/40">Deploy</div>
                <MenuItem
                  label="Vercel"
                  sub="Deploy to Vercel."
                  onClick={() => {
                    setDeployOpen(false);
                    onDeploy("vercel");
                  }}
                />
                <MenuItem
                  label="Netlify"
                  sub="Deploy to Netlify."
                  onClick={() => {
                    setDeployOpen(false);
                    onDeploy("netlify");
                  }}
                />
                <MenuItem
                  label="My server"
                  sub="Deploy to your own host."
                  onClick={() => {
                    setDeployOpen(false);
                    onDeploy("my_server");
                  }}
                />
              </div>
            ) : null}
          </div>

          {/* Profile dropdown */}
          <div className="relative overflow-visible" ref={profileRef}>
            <button
              type="button"
              onClick={() => setProfileOpen((v) => !v)}
              className="h-9 w-9 rounded-xl bg-white/5 border border-white/10 inline-flex items-center justify-center text-white/90 hover:bg-white/8 leading-none"
              aria-label="Profile"
              title="Profile"
            >
              <span className="text-[15px] leading-none">👤</span>
            </button>

            {profileOpen ? (
              <div className="cb-menu cb-menu--right">
                <div className="px-2 py-2 text-xs text-white/40">Account</div>

                <MenuItem
                  label="Billing"
                  sub="Manage plan and payment settings."
                  onClick={() => {
                    setProfileOpen(false);
                    onProfileBilling();
                  }}
                />

                <div className="my-2 h-px bg-white/10" />

                <MenuItem
                  label="Log out"
                  sub="End your session."
                  danger
                  onClick={() => {
                    setProfileOpen(false);
                    onProfileLogout();
                  }}
                />
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {/* Project Settings Modal (Share/Export live here) */}
      <Modal
        open={projSettingsOpen}
        title="Project settings"
        onClose={() => setProjSettingsOpen(false)}
      >
        <div className="space-y-3">
          <div className="text-sm text-white/75">
            Manage share links and export your project.
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button type="button" className="cb-btn cb-btn--primary" onClick={onShare}>
              Share
            </button>
            <button
              type="button"
              className="cb-btn cb-btn--secondary"
              onClick={onExport}
            >
              Export
            </button>
          </div>

          <div className="pt-2 border-t border-white/10">
            <div className="text-xs text-white/45">
              Device mode controls remain on the top bar by design.
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
}
