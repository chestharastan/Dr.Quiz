import type { NextConfig } from "next";

const backendUrl = (
  process.env.BACKEND_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const allowedDevOrigins = (
  process.env.ALLOWED_DEV_ORIGINS ?? "127.0.0.1,172.20.10.4"
)
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  allowedDevOrigins,
  // Development-only badge; top-left keeps it off the phone tab bar and the sidebar account row.
  devIndicators: { position: "top-left" },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
