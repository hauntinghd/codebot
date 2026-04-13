"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  apiFetchRaw,
  apiFetch,
  clearTokens,
  storeAccessToken,
} from "../../app/lib/api";

const LOGIN_URL = "/login";

// PATHS only (never `${API_BASE}/...`)
const WHOAMI_PATH = "/auth/whoami"; // cookie session
const BOOTSTRAP_PATH = "/auth/session/bootstrap"; // cookie -> JWT
const ME_PATH = "/me"; // bearer JWT

type WhoAmIResponse = {
  authenticated: boolean;
  id?: string;
  email?: string;
  is_admin?: boolean;
};

type BootstrapResponse = {
  access_token: string;
  me?: { id: string; email: string; is_admin: boolean };
};

async function safeJson<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function meWithBearer(): Promise<boolean> {
  try {
    const res = await apiFetchRaw(ME_PATH, { method: "GET", auth: true });
    return Boolean(res.ok);
  } catch {
    return false;
  }
}

async function whoamiWithCookie(): Promise<boolean> {
  try {
    const res = await apiFetchRaw(WHOAMI_PATH, { method: "GET", auth: false });
    const data = await safeJson<WhoAmIResponse>(res);
    return Boolean(res.ok && data?.authenticated);
  } catch {
    return false;
  }
}

async function bootstrapFromCookie(): Promise<string | null> {
  try {
    const res = await apiFetchRaw(BOOTSTRAP_PATH, { method: "GET", auth: false });
    const data = await safeJson<BootstrapResponse>(res);
    if (!res.ok || !data?.access_token) return null;
    return data.access_token;
  } catch {
    return null;
  }
}

export default function AuthGate({
  children,
  redirectTo = LOGIN_URL,
  allowCookieSessionFallback = true,
}: {
  children: React.ReactNode;
  redirectTo?: string;
  allowCookieSessionFallback?: boolean;
}) {
  const ran = useRef(false);
  const [state, setState] = useState<
    "checking" | "authed" | "redirecting" | "error"
  >("checking");
  const [detail, setDetail] = useState<string>("Checking authentication…");

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const AUTH_CHECK_TIMEOUT_MS = 15_000; // if backend doesn't respond, redirect to login

    const timeoutId = setTimeout(() => {
      setState("redirecting");
      setDetail("Authentication timed out. Redirecting to login…");
      window.location.assign(redirectTo);
    }, AUTH_CHECK_TIMEOUT_MS);

    (async () => {
      try {
        setState("checking");
        setDetail("Validating access token…");

        // 1) Bearer check (if token exists, apiFetchRaw will send it)
        const okJwt = await meWithBearer();
        if (okJwt) {
          clearTimeout(timeoutId);
          setState("authed");
          return;
        }

        // If JWT failed, wipe and try cookie fallback
        clearTokens();

        // 2) Cookie-session fallback -> bootstrap -> validate bearer
        if (allowCookieSessionFallback) {
          setDetail("Checking cookie session…");
          const okCookie = await whoamiWithCookie();

          if (okCookie) {
            setDetail("Bootstrapping session…");
            const newJwt = await bootstrapFromCookie();

            if (newJwt) {
              storeAccessToken(newJwt);
              setDetail("Validating access token…");
              const ok2 = await meWithBearer();
              if (ok2) {
                clearTimeout(timeoutId);
                setState("authed");
                return;
              }
              clearTokens();
            }
          }
        }

        clearTimeout(timeoutId);
        // 3) Not authenticated
        setState("redirecting");
        window.location.assign(redirectTo);
      } catch (e: any) {
        clearTimeout(timeoutId);
        setState("error");
        setDetail(e?.message || "Auth check failed.");
        setTimeout(() => window.location.assign(redirectTo), 300);
      }
    })();

    return () => clearTimeout(timeoutId);
  }, [redirectTo, allowCookieSessionFallback]);

  if (state === "authed") return <>{children}</>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-black">
      <div className="max-w-md w-full px-6 py-8 rounded-xl border border-white/10 bg-black/20">
        <div className="text-white font-semibold">Authenticating…</div>
        <div className="text-white/70 text-sm mt-2">{detail}</div>
        {state === "error" && (
          <div className="text-red-300 text-xs mt-3">
            Something went wrong while validating your session. Redirecting to login.
          </div>
        )}
      </div>
    </div>
  );
}
