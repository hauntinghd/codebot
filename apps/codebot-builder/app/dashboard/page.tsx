"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch, getToken, clearTokens } from "../lib/api";

const BASE = "/codebot";

type UserInfo = {
  id: string;
  email: string;
  is_admin: boolean;
  plan?: string;
  subscription_status?: string;
  credits_remaining?: number;
};

export default function DashboardPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const token = getToken();
    if (!token) {
      window.location.assign(`${BASE}/login`);
      return;
    }
    try {
      const data = await apiFetch<UserInfo>("/me");
      setUser(data);
    } catch {
      clearTokens();
      window.location.assign(`${BASE}/login`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const logout = () => {
    clearTokens();
    window.location.assign(`${BASE}/login`);
  };

  if (loading || !user) {
    return (
      <div className="dash-page">
        <div className="dash-loading">
          <div className="dash-spinner" />
        </div>
        <style>{STYLES}</style>
      </div>
    );
  }

  const plan = user.plan || "none";
  const isAdmin = user.is_admin;
  const initials = (user.email?.split("@")[0]?.[0] || "U").toUpperCase();

  return (
    <div className="dash-page">
      <div className="dash-bg-mesh" />

      {/* Top Bar */}
      <header className="dash-header">
        <div className="dash-header-left">
          <div className="dash-logo">
            <span className="dash-logo-dot" />
            CodeBot
          </div>
        </div>
        <div className="dash-header-right">
          <Link href={`${BASE}/builder`} className="dash-btn-primary">
            Open Builder
          </Link>
          <button className="dash-avatar" onClick={logout} title="Sign out">
            {initials}
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="dash-hero">
        <div className="dash-hero-text">
          <h1>Welcome back{user.email ? `, ${user.email.split("@")[0]}` : ""}</h1>
          <p>Build, deploy, and manage your projects.</p>
        </div>
        <div className="dash-hero-badges">
          {isAdmin && <span className="badge badge-admin">Admin</span>}
          <span className={`badge badge-plan ${plan !== "none" ? "badge-active" : ""}`}>
            {plan === "none" ? "No Plan" : plan.charAt(0).toUpperCase() + plan.slice(1)}
          </span>
          <span className="badge badge-status">Authenticated</span>
        </div>
      </section>

      {/* Stats */}
      <section className="dash-stats">
        <div className="stat-card">
          <div className="stat-icon">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          </div>
          <div className="stat-value">{isAdmin ? "Unlimited" : plan === "none" ? "0" : user.credits_remaining ?? "—"}</div>
          <div className="stat-label">CBT Balance</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          </div>
          <div className="stat-value">38</div>
          <div className="stat-label">AI Models</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
          <div className="stat-value">5</div>
          <div className="stat-label">Audit Layers</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon cyan">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
          </div>
          <div className="stat-value">11</div>
          <div className="stat-label">Categories</div>
        </div>
      </section>

      {/* Action Grid */}
      <section className="dash-grid">
        <Link href={`${BASE}/builder`} className="action-card action-primary">
          <div className="action-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </div>
          <div className="action-content">
            <h3>Start Building</h3>
            <p>Launch the AI code builder with 38 frontier models</p>
          </div>
          <span className="action-arrow">&rarr;</span>
        </Link>

        <Link href={`${BASE}/account`} className="action-card">
          <div className="action-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
          </div>
          <div className="action-content">
            <h3>Account</h3>
            <p>Manage your profile and API keys</p>
          </div>
          <span className="action-arrow">&rarr;</span>
        </Link>

        <Link href={`${BASE}/account/upgrade`} className="action-card">
          <div className="action-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          </div>
          <div className="action-content">
            <h3>Upgrade Plan</h3>
            <p>{plan === "none" ? "Choose a plan to start building" : "Manage your subscription"}</p>
          </div>
          <span className="action-arrow">&rarr;</span>
        </Link>

        <Link href={`${BASE}/settings`} className="action-card">
          <div className="action-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          </div>
          <div className="action-content">
            <h3>Settings</h3>
            <p>Configure models, API keys, and preferences</p>
          </div>
          <span className="action-arrow">&rarr;</span>
        </Link>
      </section>

      <style>{STYLES}</style>
    </div>
  );
}

const STYLES = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  a { text-decoration: none; color: inherit; }

  .dash-page {
    min-height: 100vh;
    background: #050a12;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    padding: 0 24px 60px;
    position: relative;
    overflow: hidden;
  }
  .dash-bg-mesh {
    position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 80% 50% at 20% 20%, rgba(99,102,241,0.06), transparent),
      radial-gradient(ellipse 60% 40% at 80% 80%, rgba(6,182,212,0.04), transparent);
  }
  .dash-loading {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }
  .dash-spinner {
    width: 32px; height: 32px;
    border: 3px solid rgba(255,255,255,0.1);
    border-top-color: rgba(99,102,241,0.8);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .dash-header {
    position: relative; z-index: 10;
    display: flex; align-items: center; justify-content: space-between;
    max-width: 1100px; margin: 0 auto;
    padding: 20px 0;
  }
  .dash-logo {
    display: flex; align-items: center; gap: 8px;
    font-size: 15px; font-weight: 600; color: #a5b4fc;
    padding: 6px 14px; border-radius: 100px;
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15);
  }
  .dash-logo-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #818cf8;
    box-shadow: 0 0 8px rgba(129,140,248,0.5);
  }
  .dash-header-right { display: flex; gap: 10px; align-items: center; }
  .dash-btn-primary {
    height: 40px; padding: 0 20px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #6366f1, #4f46e5); color: white;
    font-size: 14px; font-weight: 600; cursor: pointer; display: flex; align-items: center;
    box-shadow: 0 4px 12px -2px rgba(99,102,241,0.3);
    transition: all 0.15s;
  }
  .dash-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px -2px rgba(99,102,241,0.4); }
  .dash-avatar {
    width: 40px; height: 40px; border-radius: 50%; border: none;
    background: rgba(99,102,241,0.15); color: #a5b4fc;
    font-size: 14px; font-weight: 700; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.15s;
  }
  .dash-avatar:hover { background: rgba(99,102,241,0.25); }

  .dash-hero {
    position: relative; z-index: 1;
    max-width: 1100px; margin: 20px auto 40px;
    padding: 48px 40px; border-radius: 20px;
    background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.04));
    border: 1px solid rgba(255,255,255,0.06);
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;
  }
  .dash-hero h1 { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }
  .dash-hero p { margin-top: 8px; font-size: 15px; color: rgba(148,163,184,0.7); }
  .dash-hero-badges { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge {
    padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5);
  }
  .badge-admin { background: rgba(168,85,247,0.12); color: #c084fc; }
  .badge-active { background: rgba(34,197,94,0.12); color: #86efac; }
  .badge-status { background: rgba(34,197,94,0.12); color: #86efac; }

  .dash-stats {
    position: relative; z-index: 1;
    max-width: 1100px; margin: 0 auto 32px;
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
  }
  .stat-card {
    padding: 24px; border-radius: 16px;
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.04);
    display: flex; flex-direction: column; gap: 12px;
  }
  .stat-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: rgba(99,102,241,0.1); color: #818cf8;
    display: flex; align-items: center; justify-content: center;
  }
  .stat-icon.purple { background: rgba(168,85,247,0.1); color: #a78bfa; }
  .stat-icon.green { background: rgba(34,197,94,0.1); color: #86efac; }
  .stat-icon.cyan { background: rgba(6,182,212,0.1); color: #67e8f9; }
  .stat-value { font-size: 28px; font-weight: 700; color: #f1f5f9; }
  .stat-label { font-size: 13px; color: rgba(148,163,184,0.5); }

  .dash-grid {
    position: relative; z-index: 1;
    max-width: 1100px; margin: 0 auto;
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;
  }
  .action-card {
    display: flex; align-items: center; gap: 16px;
    padding: 24px; border-radius: 16px;
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.04);
    cursor: pointer; transition: all 0.2s;
  }
  .action-card:hover {
    background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.08);
    transform: translateY(-2px);
  }
  .action-primary {
    background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(6,182,212,0.05));
    border-color: rgba(99,102,241,0.15);
    grid-column: 1 / -1;
  }
  .action-primary:hover { border-color: rgba(99,102,241,0.3); }
  .action-icon {
    width: 48px; height: 48px; border-radius: 12px; flex-shrink: 0;
    background: rgba(99,102,241,0.1); color: #818cf8;
    display: flex; align-items: center; justify-content: center;
  }
  .action-primary .action-icon { background: rgba(99,102,241,0.15); }
  .action-content { flex: 1; min-width: 0; }
  .action-content h3 { font-size: 16px; font-weight: 600; color: #f1f5f9; }
  .action-content p { font-size: 13px; color: rgba(148,163,184,0.6); margin-top: 4px; }
  .action-arrow { font-size: 18px; color: rgba(148,163,184,0.3); }

  @media (max-width: 768px) {
    .dash-stats { grid-template-columns: repeat(2, 1fr); }
    .dash-grid { grid-template-columns: 1fr; }
    .dash-hero { padding: 32px 24px; }
    .dash-hero h1 { font-size: 22px; }
  }
`;
