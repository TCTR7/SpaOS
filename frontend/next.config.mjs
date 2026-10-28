/** @type {import('next').NextConfig} */
const qa = process.env.SPAOS_QA_MODE === "1";
const runId = process.env.SPAOS_QA_RUN_ID || "";
if (qa && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(runId)) {
  throw new Error("QA frontend requires a canonical SPAOS_QA_RUN_ID");
}
const backendOrigin = process.env.BACKEND_INTERNAL_URL || "http://localhost:8001";
if (qa) {
  const backend = new URL(backendOrigin);
  if (backend.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(backend.hostname)
      || !backend.port || ["8000", "8001", "3000"].includes(backend.port)
      || backend.username || backend.password || backend.search || backend.hash || backend.pathname !== "/") {
    throw new Error("QA frontend requires a disposable loopback backend origin");
  }
}

const nextConfig = {
  reactStrictMode: true,
  ...(qa ? {
    distDir: `.next-qa/${runId}`,
    typescript: { tsconfigPath: `.qa/tsconfig.${runId}.json` },
  } : {}),
  async headers() {
    return qa ? [{
      source: "/admin/login",
      headers: [{ key: "X-SpaOS-QA-Run-ID", value: runId }],
    }] : [];
  },
  async rewrites() {
    return {beforeFiles:[
      {source:"/s/:spa_slug/admin/:path*",destination:"/admin/:path*"},
      {source:"/s/:spa_slug/b/:tenant_slug/:path*",destination:"/:tenant_slug/:path*"},
      {source:"/s/:spa_slug",destination:"/"},
    ],afterFiles:[
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ],fallback:[]};
  },
};

export default nextConfig;
