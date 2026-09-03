import type { NextConfig } from "next";

// TASK-013: opt-in webpack bundle analyzer (ANALYZE=true npm run build)
// to audit the initial bundle (< 500KB target) and tree-shaking.
const withBundleAnalyzer =
  process.env.ANALYZE === "true"
    ? // eslint-disable-next-line @typescript-eslint/no-var-requires
      require("@next/bundle-analyzer")({ enabled: true })
    : (config: NextConfig): NextConfig => config;

const nextConfig: NextConfig = {
  output: "standalone",
};

export default withBundleAnalyzer(nextConfig);
