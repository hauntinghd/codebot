// apps/codebot-builder/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CodeBot™ Builder",
  description: "CodeBot™ builder UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="cb-bg cb-hide-overlays">
        {/* Stable root wrapper for global layout + future UI shell */}
        <div id="__cb_app" className="min-h-screen w-full">
          {children}
        </div>
      </body>
    </html>
  );
}
