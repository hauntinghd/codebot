"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { apiFetch, getToken, clearTokens } from "../lib/api";

const BASE = "/codebot";

type UserInfo = { id: string; email: string; is_admin: boolean; plan?: string; credits_remaining?: number };

const MODELS = [
  { id: "claude-opus-4-6",   label: "Claude Opus 4.6",   tier: "frontier" },
  { id: "gpt-5",             label: "GPT-5",              tier: "frontier" },
  { id: "claude-sonnet-4.5", label: "Claude Sonnet 4.5",  tier: "premium"  },
  { id: "gpt-4.1",           label: "GPT-4.1",            tier: "premium"  },
  { id: "deepseek-v3.1",     label: "DeepSeek V3.1",      tier: "premium"  },
  { id: "gemini-2.5-flash",  label: "Gemini Flash",       tier: "fast"     },
  { id: "claude-haiku-4.5",  label: "Claude Haiku 4.5",   tier: "fast"     },
];

const TIER_COLORS: Record<string, string> = { frontier: "#c084fc", premium: "#60a5fa", fast: "#86efac" };

export default function DashboardPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("claude-sonnet-4.5");
  const [modelOpen, setModelOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const modelRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) { window.location.assign(`${BASE}/login`); return; }
    try {
      const data = await apiFetch<UserInfo>("/me");
      setUser(data);
    } catch { clearTokens(); window.location.assign(`${BASE}/login`); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) setModelOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const logout = () => { clearTokens(); window.location.assign(`${BASE}/login`); };

  const goBuilder = (mode: "build" | "plan") => {
    const params = new URLSearchParams({ prompt, model: selectedModel, mode });
    window.location.assign(`${BASE}/builder/?${params.toString()}`);
  };

  const currentModel = MODELS.find(m => m.id === selectedModel) || MODELS[2];

  if (loading) return (
    <div className="d-page"><div className="d-load"><div className="d-spin" /></div><style>{CSS}</style></div>
  );

  return (
    <div className="d-page">
      <div className="d-bg" />

      {/* Top bar */}
      <header className="d-top">
        <div className="d-logo"><span className="d-dot" />CodeBot</div>
        <div className="d-top-right">
          <button className="d-signout" onClick={logout}>Sign Out</button>
          <div className="d-menu-wrap" ref={menuRef}>
            <button className="d-hamburger" onClick={() => setMenuOpen(v => !v)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            </button>
            {menuOpen && (
              <div className="d-dropdown d-dropdown-menu">
                {[
                  { href: `${BASE}/account/`, label: "Account" },
                  { href: `${BASE}/account/upgrade/`, label: "Upgrade / Billing" },
                  { href: `${BASE}/settings/`, label: "Settings" },
                  { href: `${BASE}/terms/`, label: "Terms of Service" },
                ].map(item => (
                  <a key={item.href} href={item.href} className="d-drop-item">{item.label}</a>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="d-hero">
        <h1 className="d-headline">
          What will you <em>build</em> today?
        </h1>
        <p className="d-sub">
          Prompt, preview, and deploy full-stack apps with AI.
        </p>
      </div>

      {/* Prompt box */}
      <div className="d-prompt-wrap">
        <div className="d-prompt-card">
          <textarea
            ref={inputRef}
            className="d-textarea"
            placeholder="Describe what you want to build..."
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && prompt.trim()) { e.preventDefault(); goBuilder("build"); } }}
            rows={3}
          />
          <div className="d-prompt-bar">
            {/* Model picker */}
            <div className="d-model-wrap" ref={modelRef}>
              <button className="d-model-btn" onClick={() => setModelOpen(v => !v)}>
                <span className="d-tier-dot" style={{ background: TIER_COLORS[currentModel.tier] }} />
                {currentModel.label}
                <span className="d-caret">&#9662;</span>
              </button>
              {modelOpen && (
                <div className="d-dropdown d-dropdown-model">
                  {(["frontier", "premium", "fast"] as const).map(tier => (
                    <div key={tier}>
                      <div className="d-drop-header" style={{ color: TIER_COLORS[tier] }}>{tier.toUpperCase()}</div>
                      {MODELS.filter(m => m.tier === tier).map(m => (
                        <button key={m.id} className={`d-drop-item ${m.id === selectedModel ? "active" : ""}`}
                          onClick={() => { setSelectedModel(m.id); setModelOpen(false); }}>
                          {m.label}
                          {m.id === selectedModel && <span className="d-check">&#10003;</span>}
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Plan button */}
            <button className="d-plan-btn" onClick={() => prompt.trim() && goBuilder("plan")}>
              Plan
            </button>

            {/* Build button */}
            <button className="d-build-btn" onClick={() => prompt.trim() && goBuilder("build")} disabled={!prompt.trim()}>
              Build now &#9654;
            </button>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      {user && (
        <div className="d-stats-row">
          <div className="d-stat">
            <span className="d-stat-val">{user.is_admin ? "Unlimited" : user.credits_remaining ?? 0}</span>
            <span className="d-stat-label">CBT Balance</span>
          </div>
          <div className="d-stat">
            <span className="d-stat-val">38</span>
            <span className="d-stat-label">AI Models</span>
          </div>
          <div className="d-stat">
            <span className="d-stat-val">{user.plan === "none" ? "Free" : user.plan || "Free"}</span>
            <span className="d-stat-label">Plan</span>
          </div>
        </div>
      )}

      <style>{CSS}</style>
    </div>
  );
}

const CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  a { text-decoration: none; color: inherit; }

  .d-page {
    min-height: 100vh; background: #050a12; color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    display: flex; flex-direction: column; align-items: center;
    position: relative; overflow: hidden;
  }
  .d-bg {
    position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background: radial-gradient(ellipse 70% 50% at 50% 30%, rgba(99,102,241,0.06), transparent),
                radial-gradient(ellipse 50% 40% at 80% 80%, rgba(6,182,212,0.04), transparent);
  }
  .d-load { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .d-spin {
    width: 28px; height: 28px; border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #818cf8; border-radius: 50%; animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Top bar */
  .d-top {
    position: relative; z-index: 10; width: 100%; max-width: 900px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 24px;
  }
  .d-logo {
    display: flex; align-items: center; gap: 8px;
    font-size: 14px; font-weight: 600; color: #a5b4fc;
    padding: 5px 12px; border-radius: 100px;
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15);
  }
  .d-dot { width: 6px; height: 6px; border-radius: 50%; background: #818cf8; }
  .d-top-right { display: flex; align-items: center; gap: 8px; }
  .d-signout {
    height: 36px; padding: 0 16px; border-radius: 8px;
    border: 1px solid rgba(239,68,68,0.25); background: rgba(239,68,68,0.06);
    color: #fca5a5; font-size: 13px; font-weight: 500; cursor: pointer; font-family: inherit;
  }
  .d-signout:hover { background: rgba(239,68,68,0.12); }
  .d-hamburger {
    width: 36px; height: 36px; border-radius: 8px; border: none;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7);
    cursor: pointer; display: flex; align-items: center; justify-content: center;
  }
  .d-hamburger:hover { background: rgba(255,255,255,0.1); }
  .d-menu-wrap { position: relative; }

  /* Hero */
  .d-hero {
    position: relative; z-index: 1; text-align: center;
    margin-top: 60px; padding: 0 24px;
  }
  .d-headline {
    font-size: 42px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15;
    color: #f1f5f9;
  }
  .d-headline em {
    font-style: italic;
    background: linear-gradient(135deg, #818cf8, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }
  .d-sub { margin-top: 12px; font-size: 16px; color: rgba(148,163,184,0.65); }

  /* Prompt */
  .d-prompt-wrap {
    position: relative; z-index: 1; width: 100%; max-width: 680px;
    margin-top: 40px; padding: 0 24px;
  }
  .d-prompt-card {
    border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
    background: rgba(15,23,42,0.6); backdrop-filter: blur(20px);
    overflow: hidden;
  }
  .d-textarea {
    width: 100%; padding: 20px; border: none; background: transparent;
    color: #e2e8f0; font-size: 15px; font-family: inherit; resize: none;
    outline: none; min-height: 80px;
  }
  .d-textarea::placeholder { color: rgba(148,163,184,0.35); }

  .d-prompt-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.05);
  }

  /* Model picker */
  .d-model-wrap { position: relative; }
  .d-model-btn {
    display: flex; align-items: center; gap: 6px;
    height: 34px; padding: 0 12px; border-radius: 8px; border: none;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.8);
    font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
    white-space: nowrap;
  }
  .d-model-btn:hover { background: rgba(255,255,255,0.1); }
  .d-tier-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .d-caret { font-size: 8px; opacity: 0.5; margin-left: 2px; }

  /* Plan button */
  .d-plan-btn {
    height: 34px; padding: 0 14px; border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.1); background: transparent;
    color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 500;
    cursor: pointer; font-family: inherit; margin-left: auto;
  }
  .d-plan-btn:hover { background: rgba(255,255,255,0.06); }

  /* Build button */
  .d-build-btn {
    height: 38px; padding: 0 22px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white;
    font-size: 14px; font-weight: 700; cursor: pointer; font-family: inherit;
    display: flex; align-items: center; gap: 6px;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
    transition: all 0.15s;
  }
  .d-build-btn:hover:not(:disabled) { background: linear-gradient(135deg, #3b82f6, #2563eb); transform: translateY(-1px); }
  .d-build-btn:disabled { opacity: 0.4; cursor: default; }

  /* Dropdowns */
  .d-dropdown {
    position: absolute; z-index: 100; border-radius: 12px;
    background: rgba(16,20,28,0.98); border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 16px 48px rgba(0,0,0,0.6); overflow: hidden;
    min-width: 180px;
  }
  .d-dropdown-model { bottom: 42px; left: 0; min-width: 220px; }
  .d-dropdown-menu { top: 42px; right: 0; min-width: 200px; }
  .d-drop-header {
    padding: 8px 14px 4px; font-size: 10px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
  }
  .d-drop-item {
    display: flex; align-items: center; width: 100%;
    padding: 8px 14px; border: none; background: transparent;
    color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 500;
    cursor: pointer; text-align: left; font-family: inherit;
  }
  .d-drop-item:hover, .d-drop-item.active { background: rgba(255,255,255,0.06); }
  .d-check { margin-left: auto; color: #86efac; font-size: 12px; }

  /* Stats */
  .d-stats-row {
    position: relative; z-index: 1;
    display: flex; gap: 32px; margin-top: 48px;
    padding: 0 24px;
  }
  .d-stat { display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .d-stat-val { font-size: 20px; font-weight: 700; color: #e2e8f0; }
  .d-stat-label { font-size: 12px; color: rgba(148,163,184,0.45); }

  @media (max-width: 640px) {
    .d-headline { font-size: 28px; }
    .d-prompt-bar { flex-wrap: wrap; }
    .d-stats-row { gap: 20px; }
  }
`;
