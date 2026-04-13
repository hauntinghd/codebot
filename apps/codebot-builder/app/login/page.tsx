"use client";

import React, { useState } from "react";

// Use backend URL directly if configured, otherwise try relative
// Backend URL — Vercel rewrites /codebot/api/* to Render backend
// Trailing slash required because Next.js trailingSlash:true redirects without it
const API = (process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "").trim() || "/codebot/api";
const LOGIN_URL = `${API}/auth/login/`;
const REGISTER_URL = `${API}/auth/register/`;

function storeTokens(access: string, refresh?: string) {
  try {
    localStorage.setItem("access_token", access);
    localStorage.setItem("codebot_access_token", access);
    localStorage.setItem("cb_access_token", access);
    if (refresh) localStorage.setItem("cb_refresh_token", refresh);
  } catch {}
}

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const url = mode === "login" ? LOGIN_URL : REGISTER_URL;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        // Auto-register on "Invalid credentials" if in login mode
        if (mode === "login" && res.status === 401 && data?.detail === "Invalid credentials") {
          // Try registering
          const regRes = await fetch(REGISTER_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            credentials: "include",
            body: JSON.stringify({ email: email.trim(), password }),
          });
          const regData = await regRes.json().catch(() => null);
          if (regRes.ok && regData?.access_token) {
            storeTokens(regData.access_token, regData.refresh_token);
            window.location.assign("/codebot/");
            return;
          }
          // If register also fails, show original error
        }
        const msg = data?.detail || data?.message || `Error ${res.status}`;
        throw new Error(msg);
      }

      if (data?.access_token) {
        storeTokens(data.access_token, data.refresh_token);
        window.location.assign("/codebot/");
      } else {
        throw new Error("No access token received");
      }
    } catch (err: any) {
      if (err.message?.includes("NetworkError") || err.message?.includes("fetch")) {
        setError("Cannot reach server. Make sure the backend is running.");
      } else {
        setError(err.message || "Something went wrong");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      {/* Animated gradient background */}
      <div className="bg-mesh" />
      <div className="bg-grid" />

      {/* Floating orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="login-container">
        {/* Left — branding */}
        <div className="brand-panel">
          <div className="brand-content">
            <div className="brand-badge">
              <span className="badge-dot" />
              CodeBot
            </div>
            <h1 className="brand-headline">
              Build production apps<br />
              <span className="headline-gradient">with AI that actually works.</span>
            </h1>
            <p className="brand-sub">
              38 frontier AI models across 11 categories.
              5-layer self-auditing pipeline. Ship production apps — first try.
            </p>
            <div className="brand-stats">
              <div className="stat">
                <div className="stat-num">38</div>
                <div className="stat-label">AI Models</div>
              </div>
              <div className="stat">
                <div className="stat-num">11</div>
                <div className="stat-label">Categories</div>
              </div>
              <div className="stat">
                <div className="stat-num">5</div>
                <div className="stat-label">Audit Layers</div>
              </div>
            </div>
          </div>
          <div className="brand-footer">
            <span className="nyptid">NYPTID Industries</span>
          </div>
        </div>

        {/* Right — form */}
        <div className="form-panel">
          <div className="form-inner">
            <h2 className="form-title">
              {mode === "login" ? "Welcome back" : "Create account"}
            </h2>
            <p className="form-sub">
              {mode === "login"
                ? "Sign in to access your projects and CBT balance."
                : "Start building with the world's best AI models."}
            </p>

            <form onSubmit={handleSubmit} className="form">
              <div className="field">
                <label className="label" htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  className="input"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                />
              </div>
              <div className="field">
                <label className="label" htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  className="input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  minLength={6}
                />
              </div>

              {error && (
                <div className="error-box">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M8 4.5v4M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  {error}
                </div>
              )}

              <button type="submit" className="submit-btn" disabled={loading}>
                {loading ? (
                  <span className="spinner" />
                ) : mode === "login" ? (
                  "Sign In"
                ) : (
                  "Create Account"
                )}
              </button>
            </form>

            <div className="switch-mode">
              {mode === "login" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button type="button" className="link-btn" onClick={() => { setMode("register"); setError(null); }}>
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button type="button" className="link-btn" onClick={() => { setMode("login"); setError(null); }}>
                    Sign in
                  </button>
                </>
              )}
            </div>

            <div className="terms">
              By continuing, you agree to our{" "}
              <a href="/codebot/terms">Terms of Service</a>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }

        .login-page {
          min-height: 100vh;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          position: relative;
          overflow: hidden;
          background: #050a12;
          font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
        }

        .bg-mesh {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 80% 60% at 20% 30%, rgba(99,102,241,0.08), transparent),
            radial-gradient(ellipse 60% 40% at 80% 70%, rgba(6,182,212,0.06), transparent),
            radial-gradient(ellipse 100% 80% at 50% 50%, rgba(15,23,42,1), transparent);
          z-index: 0;
        }

        .bg-grid {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
          background-size: 48px 48px;
          z-index: 0;
        }

        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          z-index: 0;
          animation: float 20s ease-in-out infinite;
        }
        .orb-1 {
          width: 400px; height: 400px;
          background: rgba(99,102,241,0.12);
          top: -10%; left: -5%;
          animation-delay: 0s;
        }
        .orb-2 {
          width: 300px; height: 300px;
          background: rgba(6,182,212,0.08);
          bottom: -5%; right: -5%;
          animation-delay: -7s;
        }
        .orb-3 {
          width: 200px; height: 200px;
          background: rgba(168,85,247,0.06);
          top: 40%; right: 20%;
          animation-delay: -14s;
        }
        @keyframes float {
          0%, 100% { transform: translate(0, 0); }
          33% { transform: translate(30px, -20px); }
          66% { transform: translate(-20px, 15px); }
        }

        .login-container {
          position: relative;
          z-index: 1;
          display: flex;
          width: 100%;
          max-width: 920px;
          border-radius: 24px;
          overflow: hidden;
          background: rgba(15,23,42,0.6);
          backdrop-filter: blur(40px);
          border: 1px solid rgba(255,255,255,0.06);
          box-shadow:
            0 40px 100px -20px rgba(0,0,0,0.8),
            0 0 0 1px rgba(255,255,255,0.03),
            inset 0 1px 0 rgba(255,255,255,0.04);
        }

        /* ---- Brand Panel ---- */
        .brand-panel {
          flex: 1;
          padding: 40px 32px 28px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          background: linear-gradient(135deg, rgba(99,102,241,0.05), rgba(6,182,212,0.03));
          border-right: 1px solid rgba(255,255,255,0.04);
          min-width: 0;
        }

        .brand-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          border-radius: 100px;
          background: rgba(99,102,241,0.1);
          border: 1px solid rgba(99,102,241,0.2);
          color: #a5b4fc;
          font-size: 13px;
          font-weight: 600;
          letter-spacing: 0.02em;
          width: fit-content;
          margin-bottom: 28px;
        }
        .badge-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: #818cf8;
          box-shadow: 0 0 8px rgba(129,140,248,0.5);
        }

        .brand-headline {
          font-size: 28px;
          font-weight: 700;
          color: #f1f5f9;
          line-height: 1.25;
          letter-spacing: -0.025em;
          margin: 0;
        }
        .headline-gradient {
          background: linear-gradient(135deg, #818cf8, #06b6d4);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .brand-sub {
          margin-top: 16px;
          font-size: 15px;
          color: rgba(148,163,184,0.85);
          line-height: 1.6;
        }

        .brand-stats {
          display: flex;
          gap: 24px;
          margin-top: 28px;
        }
        .stat-num {
          font-size: 24px;
          font-weight: 700;
          color: #e2e8f0;
        }
        .stat-label {
          font-size: 12px;
          color: rgba(148,163,184,0.6);
          margin-top: 2px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .brand-capabilities {
          display: none;
        }
        /* removed cap-tags */

        .brand-footer {
          margin-top: 20px;
        }
        .nyptid {
          font-size: 12px;
          color: rgba(148,163,184,0.3);
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        /* ---- Form Panel ---- */
        .form-panel {
          flex: 1;
          padding: 40px 32px;
          display: flex;
          align-items: center;
          min-width: 0;
        }
        .form-inner { width: 100%; }

        .form-title {
          font-size: 26px;
          font-weight: 700;
          color: #f1f5f9;
          margin: 0 0 8px;
          letter-spacing: -0.02em;
        }
        .form-sub {
          font-size: 14px;
          color: rgba(148,163,184,0.7);
          margin: 0 0 32px;
        }

        .form { display: flex; flex-direction: column; gap: 20px; }

        .field { display: flex; flex-direction: column; gap: 6px; }
        .label {
          font-size: 13px;
          font-weight: 500;
          color: rgba(203,213,225,0.8);
        }
        .input {
          width: 100%;
          height: 48px;
          padding: 0 16px;
          border-radius: 12px;
          border: 1px solid rgba(255,255,255,0.08);
          background: rgba(15,23,42,0.5);
          color: #e2e8f0;
          font-size: 14px;
          outline: none;
          transition: all 0.2s;
          font-family: inherit;
          box-sizing: border-box;
        }
        .input::placeholder { color: rgba(148,163,184,0.3); }
        .input:focus {
          border-color: rgba(99,102,241,0.5);
          box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
        }

        .error-box {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          border-radius: 12px;
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.15);
          color: #fca5a5;
          font-size: 13px;
          line-height: 1.4;
        }
        .error-box svg { flex-shrink: 0; color: #f87171; }

        .submit-btn {
          width: 100%;
          height: 48px;
          border-radius: 12px;
          border: none;
          background: linear-gradient(135deg, #6366f1, #4f46e5);
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          font-family: inherit;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px -2px rgba(99,102,241,0.3);
        }
        .submit-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, #818cf8, #6366f1);
          box-shadow: 0 6px 20px -2px rgba(99,102,241,0.4);
          transform: translateY(-1px);
        }
        .submit-btn:active:not(:disabled) {
          transform: translateY(0);
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .spinner {
          width: 20px; height: 20px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .switch-mode {
          margin-top: 24px;
          text-align: center;
          font-size: 13px;
          color: rgba(148,163,184,0.6);
        }
        .link-btn {
          background: none;
          border: none;
          color: #818cf8;
          font-weight: 600;
          cursor: pointer;
          font-size: 13px;
          font-family: inherit;
          padding: 0;
        }
        .link-btn:hover { color: #a5b4fc; text-decoration: underline; }

        .terms {
          margin-top: 20px;
          text-align: center;
          font-size: 11px;
          color: rgba(148,163,184,0.3);
        }
        .terms a {
          color: rgba(148,163,184,0.45);
          text-decoration: none;
        }
        .terms a:hover { text-decoration: underline; }

        /* ---- Responsive ---- */
        @media (max-width: 768px) {
          .login-container {
            flex-direction: column;
            max-width: 480px;
          }
          .brand-panel {
            padding: 32px 28px 24px;
            border-right: none;
            border-bottom: 1px solid rgba(255,255,255,0.04);
          }
          .brand-headline { font-size: 24px; }
          .brand-stats { gap: 20px; }
          .stat-num { font-size: 22px; }
          .form-panel { padding: 32px 28px; }
        }
      `}</style>
    </div>
  );
}
