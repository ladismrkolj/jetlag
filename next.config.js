/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: true,
  },
  // Skip ESLint during `next build` (faster/avoids lint failures in CI/servers)
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Optional: also skip TypeScript build errors (uncomment if desired)
  typescript: {
   ignoreBuildErrors: true,
  },
}

module.exports = nextConfig
