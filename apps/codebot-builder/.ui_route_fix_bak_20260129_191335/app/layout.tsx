// apps/codebot-builder/app/layout.tsx
import "./globals.css";

export const metadata = {
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
      <body className="cb-bg cb-hide-overlays">{children}</body>
    </html>
  );
}
