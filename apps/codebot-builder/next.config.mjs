import path from "path";
import { fileURLToPath } from "url";

/** @type {import("next").NextConfig} */
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
const nextConfig = {
  basePath: "/codebot",
  assetPrefix: "/codebot",
  trailingSlash: true,
  reactStrictMode: true,
  images: { unoptimized: true },
  // Resolve Turbopack root to project root (monorepo)
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
  async rewrites() {
    if (backendUrl) {
      return [
        { source: "/codebot/api/:path*", destination: `${backendUrl}/codebot/api/:path*` },
        { source: "/api/:path*", destination: `${backendUrl}/codebot/api/:path*` },
      ];
    }
    return [];
  },
};
export default nextConfig;
