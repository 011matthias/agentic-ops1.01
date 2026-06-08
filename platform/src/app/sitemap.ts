import type { MetadataRoute } from "next";

const BASE = "https://unpauseai.com";

// Stable marketing routes only. Prospect-specific /proposals/[slug],
// transactional /buy/* pages, and *-thank-you pages are intentionally
// excluded so prospect names and post-action pages stay out of the index.
const ROUTES = [
  "",
  "/services",
  "/work",
  "/automations",
  "/oneproposal",
  "/about",
  "/contact",
  "/assessment",
  "/privacy",
  "/terms",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map((path) => ({
    url: `${BASE}${path}`,
    lastModified,
    changeFrequency: "monthly",
    priority: path === "" ? 1 : 0.7,
  }));
}
