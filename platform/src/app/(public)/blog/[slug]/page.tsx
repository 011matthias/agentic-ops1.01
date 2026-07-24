import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllPosts, getPostBySlug } from "@/content/blog";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const posts = getAllPosts();
  return posts.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) return { title: "Post Not Found" };

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
    },
  };
}

const categoryColors: Record<string, string> = {
  "Platform Comparison": "bg-blue-bg text-blue",
  Strategy: "bg-purple-bg text-purple",
  Process: "bg-green-bg text-green",
  Technical: "bg-orange-bg text-orange",
};

function renderMarkdown(content: string): string {
  // Split into blocks by double newlines
  const blocks = content.split(/\n\n+/);
  const rendered: string[] = [];
  let i = 0;

  while (i < blocks.length) {
    const block = blocks[i].trim();
    if (!block) { i++; continue; }

    // Heading blocks
    if (block.startsWith("### ")) {
      const text = applyInline(block.replace(/^### /, ""));
      rendered.push(`<h3 class="mt-10 mb-4 text-lg font-bold text-foreground">${text}</h3>`);
      i++; continue;
    }
    if (block.startsWith("## ")) {
      const text = applyInline(block.replace(/^## /, ""));
      rendered.push(`<h2 class="mt-12 mb-5 text-xl font-extrabold text-foreground border-b-2 border-accent/20 pb-3">${text}</h2>`);
      i++; continue;
    }

    // GFM table blocks: a header row, a |---|---| separator, then data rows.
    // AEO content patterns lean on comparison tables; without this branch a
    // table renders as a paragraph of pipes. Wide tables scroll in their own
    // container so the page body never scrolls horizontally.
    if (block.startsWith("|")) {
      const rows = block.split(/\n/).map((l) => l.trim()).filter((l) => l.startsWith("|"));
      const isSeparator = rows.length >= 2 && /^\|[\s:|-]+\|$/.test(rows[1]);
      if (isSeparator) {
        const parseCells = (row: string) =>
          row.replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => applyInline(c.trim()));
        const header = parseCells(rows[0])
          .map((c) => `<th class="border-b-2 border-border px-4 py-2.5 text-left font-semibold text-foreground">${c}</th>`)
          .join("");
        const body = rows.slice(2)
          .map((row) =>
            `<tr class="border-b border-border/60">${parseCells(row)
              .map((c) => `<td class="px-4 py-2.5 align-top">${c}</td>`)
              .join("")}</tr>`)
          .join("\n");
        rendered.push(
          `<div class="my-6 overflow-x-auto rounded-lg border border-border"><table class="w-full text-sm leading-relaxed"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`,
        );
        i++; continue;
      }
    }

    // List blocks (unordered)
    if (block.match(/^- /m)) {
      const items = block.split(/\n/).filter(l => l.startsWith("- ")).map(l => {
        const text = applyInline(l.replace(/^- /, ""));
        return `<li class="flex items-start gap-2.5"><span class="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent/60"></span><span>${text}</span></li>`;
      });
      rendered.push(`<ul class="my-5 space-y-2.5 leading-relaxed">${items.join("\n")}</ul>`);
      i++; continue;
    }

    // Ordered list blocks
    if (block.match(/^\d+\. /m)) {
      const items = block.split(/\n/).filter(l => l.match(/^\d+\. /)).map(l => {
        const text = applyInline(l.replace(/^\d+\. /, ""));
        return `<li>${text}</li>`;
      });
      rendered.push(`<ol class="my-5 space-y-2.5 leading-relaxed list-decimal pl-5">${items.join("\n")}</ol>`);
      i++; continue;
    }

    // Regular paragraph
    rendered.push(`<p class="my-5 leading-[1.8]">${applyInline(block.replace(/\n/g, " "))}</p>`);
    i++;
  }

  return rendered.join("\n");
}

function applyInline(text: string): string {
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>');
  // Italic
  text = text.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code class="rounded bg-surface-hover px-1.5 py-0.5 text-[0.8125rem] font-mono text-foreground">$1</code>');
  // Links
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-accent underline underline-offset-2 hover:text-accent-light transition-colors">$1</a>');
  return text;
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const post = getPostBySlug(slug);

  if (!post) notFound();

  const allPosts = getAllPosts();
  const currentIndex = allPosts.findIndex((p) => p.slug === slug);
  const prevPost = currentIndex < allPosts.length - 1 ? allPosts[currentIndex + 1] : null;
  const nextPost = currentIndex > 0 ? allPosts[currentIndex - 1] : null;

  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.date,
    author: { "@type": "Person", name: post.author || "Nicolas Neumann" },
    publisher: { "@type": "Organization", name: "UnpauseAI", url: "https://unpauseai.com" },
    url: `https://unpauseai.com/blog/${slug}`,
  };

  return (
    <div className="flex flex-col">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />
      <article className="mx-auto max-w-3xl px-6 py-20">
        {/* Header */}
        <div className="mb-10">
          <Link
            href="/blog"
            className="mb-6 inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-accent"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
            All posts
          </Link>

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                categoryColors[post.category] || "bg-blue-bg text-blue"
              }`}
            >
              {post.category}
            </span>
            <span className="text-xs text-muted">
              {new Date(post.date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </span>
          </div>

          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            {post.title}
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-muted">
            {post.excerpt}
          </p>
        </div>

        {/* Content */}
        <div
          className="text-muted"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content) }}
        />
      </article>

      {/* Post Navigation */}
      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10 sm:flex-row sm:justify-between">
          {prevPost ? (
            <Link
              href={`/blog/${prevPost.slug}`}
              className="group flex flex-col rounded-xl border border-border bg-surface p-4 transition-all hover:-translate-y-0.5 hover:shadow-md sm:max-w-[48%]"
            >
              <span className="mb-1 text-xs text-muted">&larr; Previous</span>
              <span className="text-sm font-semibold transition-colors group-hover:text-accent">
                {prevPost.title}
              </span>
            </Link>
          ) : (
            <div />
          )}
          {nextPost ? (
            <Link
              href={`/blog/${nextPost.slug}`}
              className="group flex flex-col items-end rounded-xl border border-border bg-surface p-4 text-right transition-all hover:-translate-y-0.5 hover:shadow-md sm:max-w-[48%]"
            >
              <span className="mb-1 text-xs text-muted">Next &rarr;</span>
              <span className="text-sm font-semibold transition-colors group-hover:text-accent">
                {nextPost.title}
              </span>
            </Link>
          ) : (
            <div />
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-16 text-center">
          <h2 className="text-xl font-bold">Want to put this into practice?</h2>
          <p className="text-muted">
            Tell us about your workflow and we&rsquo;ll assess it within 24 hours.
          </p>
          <Link
            href="/assessment"
            className="mt-2 rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request Assessment: $1
          </Link>
        </div>
      </section>
    </div>
  );
}
