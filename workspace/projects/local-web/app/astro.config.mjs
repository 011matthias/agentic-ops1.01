// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// One Astro project serving many bespoke single-page demos.
// Each site owns its route, theme tokens, and section components.
// `site` is set at deploy time (Fly URL) for canonical + JSON-LD.
export default defineConfig({
  site: process.env.SITE_URL ?? "https://local-web.fly.dev",
  output: "static",
  vite: {
    plugins: [tailwindcss()],
  },
  image: {
    // Allow remote curated stock (Unsplash/Pexels) to be optimized at build.
    domains: ["images.unsplash.com", "images.pexels.com"],
  },
});
