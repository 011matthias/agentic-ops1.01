import fs from "fs";
import path from "path";
import matter from "gray-matter";

export interface ProposalPhase {
  name: string;
  weeks: string;
  price?: string;
  items: string[];
}

export interface ProposalFrontmatter {
  id: string;
  slug: string;
  prospect: string;
  contact: string;
  source: "upwork" | "direct" | "linkedin" | "referral";
  source_url?: string;
  project_title: string;
  status: "draft" | "sent" | "viewed" | "won" | "lost";
  created: string;
  sent: string | null;
  value_estimate: string;
  timeline: string;
  tags: string[];
  phases?: ProposalPhase[];
}

export interface Proposal {
  frontmatter: ProposalFrontmatter;
  content: string;
}

const PROPOSALS_DIR = path.join(process.cwd(), "src", "content", "proposals");

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function extractHeadings(
  markdown: string
): { id: string; text: string; level: 2 | 3 }[] {
  const regex = /^(#{2,3})\s+(.+)$/gm;
  const headings: { id: string; text: string; level: 2 | 3 }[] = [];
  let match;
  while ((match = regex.exec(markdown)) !== null) {
    headings.push({
      id: slugify(match[2]),
      text: match[2],
      level: match[1].length as 2 | 3,
    });
  }
  return headings;
}

export function getProposalSlugs(): string[] {
  if (!fs.existsSync(PROPOSALS_DIR)) return [];
  return fs
    .readdirSync(PROPOSALS_DIR)
    .filter((file) => file.endsWith(".md"))
    .map((file) => file.replace(/\.md$/, ""));
}

export function getProposalBySlug(slug: string): Proposal | null {
  const filePath = path.join(PROPOSALS_DIR, `${slug}.md`);
  if (!fs.existsSync(filePath)) return null;

  const fileContent = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(fileContent);

  return {
    frontmatter: data as ProposalFrontmatter,
    content,
  };
}

export function getAllProposals(): Proposal[] {
  const slugs = getProposalSlugs();
  return slugs
    .map((slug) => getProposalBySlug(slug))
    .filter((p): p is Proposal => p !== null)
    .sort(
      (a, b) =>
        new Date(b.frontmatter.created).getTime() -
        new Date(a.frontmatter.created).getTime()
    );
}