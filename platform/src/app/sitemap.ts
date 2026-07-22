import type { MetadataRoute } from "next";
import { getAllPosts } from "@/content/blog";

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
  "/blog",
  "/compare",
  "/faq",
  "/pricing",
  "/contact",
  "/assessment",
  "/privacy",
  "/terms",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const staticEntries: MetadataRoute.Sitemap = ROUTES.map((path) => ({
    url: `${BASE}${path}`,
    lastModified,
    changeFrequency: "monthly",
    priority: path === "" ? 1 : 0.7,
  }));
  // Blog posts are content pages; derive them from the collection so a new
  // .md is indexed without touching this file (the 2026-07-22 drift fix:
  // /blog and friends were invisible to the crawl map the AEO remediation
  // itself created).
  const postEntries: MetadataRoute.Sitemap = getAllPosts().map((post) => ({
    url: `${BASE}/blog/${post.slug}`,
    lastModified: post.date ? new Date(post.date) : lastModified,
    changeFrequency: "yearly",
    priority: 0.6,
  }));
  return [...staticEntries, ...postEntries];
}
