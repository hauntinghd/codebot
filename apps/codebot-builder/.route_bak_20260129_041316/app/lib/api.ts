// apps/codebot-builder/app/lib/api.ts
"use client";

export const API_BASE =
  (process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "").trim() || "/codebot/api";

const TOKEN_KEYS = ["access_token", "codebot_access_token", "cb_access_token"] as const;

export class ApiError extends Error {
  status: number;
  bodyText?: string;
  constructor(message: string, status: number, bodyText?: string) {
    super(message);
    this.status = status;
    this.bodyText = bodyText;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    for (const k of TOKEN_KEYS) {
      const v = localStorage.getItem(k);
      if (v && v.trim()) return v.trim();
    }
    return null;
  } catch {
    return null;
  }
}

export function storeAccessToken(token: string) {
  if (typeof window === "undefined") return;
  try {
    for (const k of TOKEN_KEYS) localStorage.setItem(k, token);
  } catch {
    // ignore
  }
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  try {
    for (const k of TOKEN_KEYS) localStorage.removeItem(k);
  } catch {
    // ignore
  }
}

/**
 * Join API_BASE + PATH safely.
 * - Accepts absolute URLs and returns them unchanged.
 * - Accepts already-prefixed "/codebot/api/..." and returns unchanged.
 * - Normalizes slashes to avoid "//".
 */
export function joinApiUrl(pathOrUrl: string): string {
  const p0 = (pathOrUrl || "").trim();
  if (!p0) return API_BASE;

  // absolute URL: don't touch
  if (/^https?:\/\//i.test(p0)) return p0;

  const base = (API_BASE || "").trim().replace(/\/+$/, "");
  let p = p0.startsWith("/") ? p0 : `/${p0}`;

  // if caller already included the base prefix, do not add again
  if (base && (p === base || p.startsWith(base + "/"))) return p;

  // normal join
  return `${base}${p}`;
}

async function readJsonOrNull<T>(text: string): Promise<T | null> {
  try {
    return text ? (JSON.parse(text) as T) : null;
  } catch {
    return null;
  }
}

/**
 * Low-level fetch returning Response (for flows that need status handling).
 */
export async function apiFetchRaw(
  path: string,
  opts: RequestInit & { auth?: boolean } = {}
): Promise<Response> {
  const url = joinApiUrl(path);
  const headers = new Headers(opts.headers || {});
  headers.set("accept", "application/json");

  // Bearer if enabled and present
  if (opts.auth !== false) {
    const token = getToken();
    if (token) headers.set("authorization", `Bearer ${token}`);
  }

  return fetch(url, {
    ...opts,
    headers,
    credentials: "include",
    cache: "no-store",
  });
}

/**
 * JSON helper that throws ApiError on non-2xx.
 */
export async function apiFetch<T>(
  path: string,
  opts: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const res = await apiFetchRaw(path, opts);

  const text = await res.text();
  const json = await readJsonOrNull<any>(text);

  if (!res.ok) {
    const msg = json?.detail || json?.message || `Request failed: ${res.status}`;
    throw new ApiError(msg, res.status, text);
  }

  return (json ?? ({} as any)) as T;
}
