// =============================================================================
// serve.ts — Arcadia landing static file server (Bun)
//
// Serves the Astro `dist/` output with:
//   * SPA-style fallback to /index.html for unknown routes (Astro trailing
//     slash "ignore" — /en/ resolves; deep links get index).
//   * Cache headers: immutable for hashed /_astro/ assets, 30 days for
//     images/fonts, no-cache for HTML.
//   * Security headers that a static CDN would otherwise add.
//
// Run: `bun run serve.ts`  (port via PORT env, default 8080).
// =============================================================================

import { join } from "node:path";

const ROOT = join(import.meta.dir, "dist");
const PORT = Number(process.env.PORT || 8080);

const FALLBACK = "index.html";

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
};

const BASE_SECURITY = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};

function cacheFor(path: string): string {
  if (path.startsWith("/_astro/")) return "public, max-age=31536000, immutable";
  if (/\.(png|jpe?g|gif|webp|avif|svg|ico|woff2?)$/.test(path))
    return "public, max-age=2592000"; // 30 days
  return "public, must-revalidate, max-age=0, s-maxage=3600"; // HTML
}

function extToMime(path: string): string {
  const dot = path.lastIndexOf(".");
  if (dot === -1) return "application/octet-stream";
  return MIME[path.slice(dot).toLowerCase()] || "application/octet-stream";
}

Bun.serve({
  port: PORT,
  async fetch(req) {
    const url = new URL(req.url);
    const raw = decodeURIComponent(url.pathname);

    // Prevent path traversal (..) escaping the web root.
    if (raw.includes("..")) {
      return new Response("Forbidden", { status: 403 });
    }

    // Normalize: trailing slash -> index.html.
    let path = raw;
    if (path.endsWith("/")) path += "index.html";

    let file = Bun.file(join(ROOT, path));
    if (!(await file.exists())) {
      // SPA fallback (Astro trailingSlash "ignore" — deep links get index).
      file = Bun.file(join(ROOT, FALLBACK));
    }

    return new Response(file, {
      headers: {
        "Content-Type": extToMime(path),
        "Cache-Control": cacheFor(url.pathname),
        ...BASE_SECURITY,
      },
    });
  },
});

console.log(`[serve] Arcadia landing on :${PORT}`);