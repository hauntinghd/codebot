// apps/codebot-builder/app/login/page.tsx
"use client";

import React, { useEffect, useRef, useState } from "react";

const API_BASE =
  (process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "").trim() || "/codebot/api";

const OAUTH_START_URL = `${API_BASE}/auth/oauth/google`;
const BOOTSTRAP_URL = `${API_BASE}/auth/session/bootstrap`;
const WHOAMI_URL = `${API_BASE}/auth/whoami`;

type BootstrapResponse = {
  access_token: string;
  me?: { id: string; email: string; is_admin: boolean };
};

type WhoAmIResponse = {
  authenticated: boolean;
  id?: string;
  email?: string;
  is_admin?: boolean;
};

function storeAccessToken(token: string) {
  localStorage.setItem("access_token", token);
  localStorage.setItem("codebot_access_token", token);
  localStorage.setItem("cb_access_token", token);
}

function getOauthReturnFlag(): boolean {
  try {
    const qs = new URLSearchParams(window.location.search);
    return qs.get("oauth") === "1";
  } catch {
    return false;
  }
}

async function readJsonSafe<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(t);
  }
}

export default function LoginPage() {
  const ran = useRef(false);

  const [phase, setPhase] = useState<
    "ready" | "bootstrapping" | "success" | "error"
  >("ready");
  const [status, setStatus] = useState<string>("Ready.");
  const [error, setError] = useState<string | null>(null);

  const dashboardPath = "/codebot/dashboard";

  function startGoogleOAuth() {
    window.location.assign(OAUTH_START_URL);
  }

  async function whoami(): Promise<WhoAmIResponse | null> {
    try {
      const res = await fetchWithTimeout(
        WHOAMI_URL,
        {
          method: "GET",
          credentials: "include",
          cache: "no-store",
          headers: { accept: "application/json" },
        },
        8000
      );
      return await readJsonSafe<WhoAmIResponse>(res);
    } catch {
      return null;
    }
  }

  async function bootstrap(): Promise<BootstrapResponse> {
    const res = await fetchWithTimeout(
      BOOTSTRAP_URL,
      {
        method: "GET",
        credentials: "include",
        cache: "no-store",
        headers: { accept: "application/json" },
      },
      12000
    );

    const data = await readJsonSafe<BootstrapResponse>(res);
    if (!res.ok || !data?.access_token) {
      let detail = "";
      try {
        detail = await res.text();
      } catch {
        // ignore
      }
      throw new Error(
        `Bootstrap failed (HTTP ${res.status}). ${
          data ? `JSON=${JSON.stringify(data)}` : ""
        } ${detail ? `Body=${detail}` : ""}`.trim()
      );
    }
    return data;
  }

  async function finishSignIn() {
    setPhase("bootstrapping");
    setError(null);

    // keep internal status, but we do NOT render it unless error
    setStatus("Checking session…");

    const me = await whoami();
    if (me?.authenticated) {
      setStatus("Session detected — issuing JWT…");
    } else {
      setStatus("No session detected yet — attempting bootstrap…");
    }

    const boot = await bootstrap();
    storeAccessToken(boot.access_token);

    setPhase("success");
    setStatus("Signed in — redirecting…");
    window.location.assign(dashboardPath);
  }

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      if (!getOauthReturnFlag()) return;
      try {
        await finishSignIn();
      } catch (e: any) {
        setPhase("error");
        setStatus("Sign-in failed.");
        setError(e?.message || "Unknown error.");
      }
    })();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-[#0b1d3a] via-[#102a56] to-[#163b78]">
      {/* tighter, shorter card; solid enough to avoid the "bar" look */}
      <div className="w-full max-w-md rounded-2xl border border-white/15 bg-black/35 shadow-2xl backdrop-blur-xl px-7 py-6">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-white">
            CodeBot
            <span className="align-super text-sm relative -top-0.5 opacity-95">
              ™
            </span>
          </h1>

          {/* slightly lower */}
          <div className="mt-2 text-sm font-semibold text-white/85">
            by NYPTID Industries
          </div>
        </div>

        {/* center the button and keep it visually "button-like" */}
        <div className="mt-6 flex justify-center">
          <button
            className="w-full max-w-sm rounded-xl bg-blue-600 px-4 py-3 text-white font-semibold shadow-sm hover:bg-blue-700 active:bg-blue-800 disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={startGoogleOAuth}
            disabled={phase === "bootstrapping"}
          >
            Sign in with Google
          </button>
        </div>

        {/* only show anything below the button if there is an error */}
        {phase === "error" && (
          <div className="mt-4 rounded-xl border border-red-300/30 bg-red-500/10 p-3 text-sm text-red-100">
            <div className="font-semibold mb-2">Login error</div>
            <pre className="whitespace-pre-wrap break-words text-xs text-red-100/90">
              {error || status}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
