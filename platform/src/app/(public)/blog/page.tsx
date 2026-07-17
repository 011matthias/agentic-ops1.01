import type { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "@/content/blog";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Practical guides on workflow automation, platform comparisons, and building reliable systems. From the team at UnpauseAI.",
};

const categoryColors: Record<string, string> = {
  "Platform Comparison": "bg-blue-bg text-blue",
  Strategy: "bg-purple-bg text-purple",
  Process: "bg-green-bg text-green",
  Technical: "bg-orange-bg text-orange",
};

export default function BlogPage() {
  const posts = getAllPosts();

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Blog
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Automation insights
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Practical guides on workflow automation, platform comparisons, and
            lessons from building production systems.
          </p>
        </div>
      </section>

      {/* Posts */}
      <section className="mx-auto max-w-3xl px-6 pb-20">
        <div className="space-y-6">
          {posts.map((post) => (
            <ScrollReveal key={post.slug}>
              <Link
                href={`/blog/${post.slug}`}
                className="group block rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="mb-3 flex flex-wrap items-center gap-3">
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
                <h2 className="mb-2 text-lg font-bold transition-colors group-hover:text-accent">
                  {post.title}
                </h2>
                <p className="text-sm leading-relaxed text-muted">
                  {post.excerpt}
                </p>
                <span className="mt-3 inline-block text-sm font-medium text-accent">
                  Read more &rarr;
                </span>
              </Link>
            </ScrollReveal>
          ))}
        </div>

        {posts.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-muted">No posts yet. Check back soon.</p>
          </div>
        )}
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Ready to automate?
          </h2>
          <p className="max-w-lg text-muted">
            Describe your workflow and get a personalized assessment within 24 hours.
          </p>
          <Link
            href="/assessment"
            className="mt-2 rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request Assessment &mdash; $1
          </Link>
        </div>
      </section>
    </div>
  );
}
