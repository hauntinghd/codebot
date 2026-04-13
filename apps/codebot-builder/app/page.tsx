"use client";

import { useEffect } from "react";

export default function RootPage() {
  useEffect(() => {
    // If user has a token, go to dashboard. Otherwise go to login.
    const token = localStorage.getItem("access_token") || localStorage.getItem("codebot_access_token");
    if (token) {
      window.location.replace("/codebot/dashboard");
    } else {
      window.location.replace("/codebot/login");
    }
  }, []);

  return null;
}
