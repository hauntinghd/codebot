"use client";

import React from "react";

const BASE = "/codebot";

type SectionProps = { num: string; title: string; children: React.ReactNode };

function Section({ num, title, children }: SectionProps) {
  return (
    <section style={{ marginBottom: 32 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 12 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.3)", fontVariantNumeric: "tabular-nums" }}>{num}</span>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: "white", margin: 0 }}>{title}</h2>
      </div>
      <div style={{ fontSize: 14, color: "rgba(255,255,255,0.65)", lineHeight: 1.7, paddingLeft: 28 }}>
        {children}
      </div>
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul style={{ margin: "10px 0", paddingLeft: 18, listStyleType: "none" }}>
      {items.map((item) => (
        <li key={item} style={{ marginBottom: 6, display: "flex", gap: 10, alignItems: "flex-start" }}>
          <span style={{ width: 5, height: 5, borderRadius: "50%", background: "rgba(255,255,255,0.25)", marginTop: 7, flexShrink: 0 }} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function Para({ children, bold }: { children: React.ReactNode; bold?: boolean }) {
  return (
    <p style={{ margin: "0 0 12px", fontWeight: bold ? 600 : 400 }}>
      {children}
    </p>
  );
}

export default function TermsOfServicePage() {
  const lastUpdated = "January 30, 2026";

  return (
    <div style={{ minHeight: "100vh", background: "var(--cb-bg, #0b0f14)", color: "white", padding: "48px 0" }}>
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "0 28px" }}>
        {/* Back */}
        <a
          href={`${BASE}/builder`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            height: 34,
            padding: "0 14px",
            borderRadius: 8,
            background: "rgba(255,255,255,0.06)",
            color: "rgba(255,255,255,0.7)",
            fontSize: 13,
            fontWeight: 600,
            textDecoration: "none",
            marginBottom: 32,
          }}
        >
          ← Back to Builder
        </a>

        {/* Card */}
        <div
          style={{
            borderRadius: 16,
            background: "rgba(255,255,255,0.02)",
            boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)",
            padding: "40px 36px",
          }}
        >
          {/* Header */}
          <div style={{ marginBottom: 32, borderBottom: "1px solid rgba(255,255,255,0.04)", paddingBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <img src={`${BASE}/logo.png`} alt="NYPTID" width={32} height={32} style={{ borderRadius: "50%", opacity: 0.8 }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.35)", letterSpacing: "0.06em", textTransform: "uppercase" }}>NYPTID Industries</span>
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: "0 0 8px" }}>Terms of Service</h1>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>Last updated: {lastUpdated}</div>
          </div>

          {/* Sections */}
          <Section num="1." title="Agreement to Terms">
            <Para>
              By accessing or using <strong>CodeBot™</strong> (the &quot;Service&quot;), provided by{" "}
              <strong>NYPTID Industries Advanced Technologies</strong> (&quot;Company&quot;, &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;),
              you agree to be bound by these Terms of Service (&quot;Terms&quot;). If you do not agree, you may not access or use the Service.
            </Para>
            <Para>
              These Terms constitute a legally binding agreement. You represent that you have the legal capacity to enter into these Terms on your own behalf or on behalf of any entity you represent.
            </Para>
          </Section>

          <Section num="2." title="Description of Service">
            <Para>
              CodeBot™ is an AI-powered code builder platform that generates, analyzes, and deploys web applications. The Service utilizes advanced artificial intelligence to help users build software.
            </Para>
            <Para>
              You acknowledge the Service is a tool to assist you, and outcomes may vary. The Service may evolve, including changes to features, performance, and availability.
            </Para>
          </Section>

          <Section num="3." title="Account Registration">
            <Para>To use certain features, you must register for an account. When you register, you agree to:</Para>
            <BulletList items={[
              "Provide accurate, current, and complete information",
              "Maintain and promptly update your account information",
              "Maintain the security of your account credentials",
              "Accept responsibility for all activities under your account",
              "Notify us immediately of any unauthorized use",
            ]} />
            <Para>
              You are solely responsible for safeguarding your login information. We may assume that communications from your account are made by you.
            </Para>
          </Section>

          <Section num="4." title="Subscription and Payments">
            <Para>The Service offers paid subscription plans with usage-based credit consumption. By subscribing, you agree to:</Para>
            <BulletList items={[
              "Subscription fees are billed monthly",
              "You authorize us to charge your payment method for all fees",
              "Subscriptions automatically renew unless cancelled",
              "Credits are consumed based on build complexity and usage",
              "Monthly credits reset each billing cycle; purchased credits do not expire",
              "Refunds are handled on a case-by-case basis at our discretion",
            ]} />
            <Para>
              Pricing, features, and credit rates may change. Changes apply prospectively, and we will provide notice through the Service or by email.
            </Para>
          </Section>

          <Section num="5." title="Acceptable Use">
            <Para>You agree not to use the Service to engage in harmful, unlawful, or abusive behavior, including:</Para>
            <BulletList items={[
              "Generate malicious code, malware, or code intended to cause harm",
              "Violate any applicable laws, regulations, or third-party rights",
              "Infringe upon intellectual property rights of others",
              "Interfere with or disrupt the Service",
              "Attempt to gain unauthorized access to any part of the Service",
              "Use the Service for any illegal or unauthorized purpose",
              "Transmit viruses, worms, or other malicious code",
              "Harass, abuse, or harm another person or entity",
            ]} />
            <Para>
              We reserve the right to investigate suspected violations and to suspend or terminate access to the Service.
            </Para>
          </Section>

          <Section num="6." title="Intellectual Property">
            <Para>
              <strong>Your Content:</strong> You retain ownership of code, content, or materials you submit. You grant us a limited, non-exclusive, worldwide, royalty-free license to host, process, transmit, and use Your Content solely for providing and improving the Service.
            </Para>
            <Para>
              <strong>Generated Content:</strong> Code generated by the Service may be used by you for any lawful purpose. You acknowledge that similar outputs may be generated for other users, and we do not guarantee uniqueness or non-infringement.
            </Para>
          </Section>

          <Section num="7." title="Privacy">
            <Para>
              Your use of the Service is governed by our Privacy Policy. By using the Service, you consent to the collection and use of information as described therein.
            </Para>
            <Para>
              You should not submit sensitive information unless you intend it to be processed for delivering the Service.
            </Para>
          </Section>

          <Section num="8." title="Disclaimers">
            <Para bold>
              THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF ANY KIND. WE DO NOT WARRANT THAT:
            </Para>
            <BulletList items={[
              "The Service will meet your specific requirements",
              "The Service will be uninterrupted, timely, secure, or error-free",
              "Any generated code will be accurate, complete, or suitable for your purposes",
              "Any defects will be corrected",
            ]} />
            <Para>
              You are solely responsible for reviewing, testing, and validating any code generated before production use. The Company is not responsible for decisions based on Service outputs.
            </Para>
          </Section>

          <Section num="9." title="Limitation of Liability">
            <Para bold>
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, NYPTID INDUSTRIES SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, REVENUES, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES RESULTING FROM YOUR USE OF THE SERVICE.
            </Para>
            <Para>
              Our total liability shall not exceed the amount you paid in the twelve (12) months preceding the claim, or $100 USD, whichever is greater.
            </Para>
          </Section>

          <Section num="10." title="Indemnification">
            <Para>
              You agree to defend, indemnify, and hold harmless <strong>NYPTID Industries Advanced Technologies</strong> and its officers, directors, employees, and agents from any claims, liabilities, damages, losses, and expenses arising from your use of the Service or violation of these Terms.
            </Para>
          </Section>

          <Section num="11." title="Modifications to Service">
            <Para>
              We reserve the right to modify, suspend, or discontinue the Service at any time. We shall not be liable for any modification, suspension, or discontinuation.
            </Para>
            <Para>
              We may impose limits on features or restrict access to maintain quality, security, or operational integrity.
            </Para>
          </Section>

          <Section num="12." title="Changes to Terms">
            <Para>
              We may revise these Terms from time to time. Material changes will have at least 30 days' notice before taking effect.
            </Para>
            <Para>
              Your continued use after changes constitutes acceptance. If you do not agree, you must stop using the Service.
            </Para>
          </Section>

          <Section num="13." title="Termination">
            <Para>
              We may terminate or suspend your account immediately, without prior notice, for any reason including breach of these Terms. Upon termination, your right to use the Service ceases immediately.
            </Para>
            <Para>
              We may delete or retain information associated with your account as required by law or business needs.
            </Para>
          </Section>

          <Section num="14." title="Governing Law">
            <Para>
              These Terms are governed by the laws of the jurisdiction in which NYPTID Industries is established, without regard to conflict of law provisions.
            </Para>
            <Para>
              You agree that disputes will be brought in courts of competent jurisdiction in that location, and you consent to personal jurisdiction there.
            </Para>
          </Section>

          <Section num="15." title="Contact Information">
            <Para>
              Questions about these Terms? Contact us at <strong>NYPTID Industries Advanced Technologies</strong> or visit{" "}
              <a href="https://nyptidindustries.com" target="_blank" rel="noreferrer" style={{ color: "rgba(56,189,248,0.9)", textDecoration: "underline" }}>
                nyptidindustries.com
              </a>.
            </Para>
          </Section>

          {/* Footer */}
          <div style={{ marginTop: 32, paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.04)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.3)" }}>© {new Date().getFullYear()} NYPTID Industries Advanced Technologies</span>
            <a href={`${BASE}/builder`} style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", textDecoration: "none" }}>Back to Builder →</a>
          </div>
        </div>

        <div style={{ height: 48 }} />
      </div>
    </div>
  );
}
