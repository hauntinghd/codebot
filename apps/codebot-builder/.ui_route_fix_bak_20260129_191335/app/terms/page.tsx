"use client";

import React from "react";

export default function TermsPage() {
  return (
    <div className="min-h-screen cb-bg text-white">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="text-2xl font-semibold">Terms of service</div>
        <div className="mt-1 text-sm text-white/60">Draft. Replace with final legal text.</div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-white/80 space-y-4">
          <p><strong>1. Acceptance.</strong> By using CodeBot™, you agree to these terms.</p>
          <p><strong>2. Accounts.</strong> You are responsible for safeguarding access to your account.</p>
          <p><strong>3. Billing.</strong> Subscriptions and billing are handled through Stripe.</p>
          <p><strong>4. Outputs.</strong> AI outputs are provided as-is; review before production use.</p>
          <p><strong>5. Termination.</strong> We may suspend access for abuse or violations.</p>
        </div>
      </div>
    </div>
  );
}
