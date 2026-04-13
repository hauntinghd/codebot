"use client";

import React, { useEffect, useRef, useState } from "react";

const BASE = "/codebot";

export default function RootPage() {
  const ran = useRef(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const t1 = window.setTimeout(() => {
      try {
        window.location.assign(`${BASE}/login`);
      } catch {
        window.location.href = `${BASE}/login`;
      }
    }, 250);

    const t2 = window.setInterval(() => setSeconds((s) => s + 1), 1000);

    return () => {
      window.clearTimeout(t1);
      window.clearInterval(t2);
    };
  }, []);

  return (
    <div className="min-h-screen cb-bg text-white flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-black/25 shadow-2xl backdrop-blur-xl p-6">
        <div className="text-center">
          <div className="text-3xl font-black tracking-tight">
            CodeBot<span className="align-super text-xs opacity-90">™</span>
          </div>
          <div className="mt-2 text-sm text-white/65">Redirecting to login…</div>
        </div>

        <div className="mt-5 grid gap-2">
          <button className="cb-btn primary" type="button" onClick={() => window.location.assign(`${BASE}/login`)}>
            Continue
          </button>
          <button className="cb-btn" type="button" onClick={() => window.location.assign(`${BASE}/dashboard`)}>
            Open Dashboard
          </button>
        </div>

        <div className="mt-4 text-center text-xs text-white/45">
          If this doesn’t move within a few seconds, open <span className="text-white/70">{BASE}/login</span> directly.
          {seconds >= 5 ? ` (${seconds}s)` : ""}
        </div>
      </div>
    </div>
  );
}
