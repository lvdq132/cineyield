import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for Docker/Cloud Run: produces a self-contained .next/standalone dir
  output: "standalone",
};

export default nextConfig;
