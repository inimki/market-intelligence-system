import type { NextConfig } from 'next';

// The public distribution is static-only; no personal hosting account is needed.
const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/learn',
  trailingSlash: true,
};
export default nextConfig;
