# =============================================================================
# ARCADIA — landing (Astro static) — production image
#
# Simple, Dokploy-friendly: build with Bun 1.4, then serve the static output
# with Bun itself. No nginx needed.
#   * Reproducible installs via the bun.lock lockfile.
#   * Runs as non-root (oven/bun images run as the `bun` user).
#   * Serves files with cache headers for /_astro/ assets (see serve.ts).
# =============================================================================

# ---- Stage 1: build the static site ----
FROM oven/bun:1.4-alpine AS build
WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

# ---- Stage 2: runtime image (Bun only) ----
FROM oven/bun:1.4-alpine
WORKDIR /app

# Use the bun-alpine image's non-root user already set by the base image.

COPY --from=build /app/dist ./dist

# Tiny static server with proper cache headers.
COPY serve.ts .

EXPOSE 8080

CMD ["bun", "run", "serve.ts"]