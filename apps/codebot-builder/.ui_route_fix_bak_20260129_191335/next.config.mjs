/** @type {import("next").NextConfig} */
const nextConfig = {
  // CodeBot is served under /codebot behind nginx
  basePath: "/codebot",
  assetPrefix: "/codebot",

  // Keep strict mode; no impact on OAuth
  reactStrictMode: true,
  trailingSlash: true,

  // If you use images, keep them unoptimized for static-like deployment
  images: { unoptimized: true },
};

export default nextConfig;
