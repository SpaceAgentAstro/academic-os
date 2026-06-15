/** @type {import('next').NextConfig} */

// Allow the deployed API origin in connect-src so fetches are not blocked by CSP.
const apiOrigin = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Content-Security-Policy: restrict framing and object embedding, pin the icon
// CDN as the only external style/font source, and permit XHR only to self + the
// configured API. Kept moderate so Next.js' own inline runtime still works.
const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
  "font-src 'self' data: https://cdn.jsdelivr.net",
  "img-src 'self' data: blob:",
  `connect-src 'self' ${apiOrigin}`,
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
