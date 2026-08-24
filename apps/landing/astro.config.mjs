import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// https://astro.build/config
// Arcadia — landing. Built with Astro 6: zero JS by default, islands where
// needed. Deploy target: static (GitHub Pages, Cloudflare Pages, Garage S3).
export default defineConfig({
  site: "https://arcadia.archeaage.dev",
  trailingSlash: "ignore",
  integrations: [sitemap()],
});