import type { Metadata } from "next";
import Link from "next/link";
import { getDisplayableProposals } from "@/lib/proposals";

export const metadata: Metadata = {
  title: "Work - UnpauseAI",
  description:
    "Automation projects we've built for clients across healthcare, PR, finance, and media industries.",
};

const tagLabels: Record<string, string> = {
  "n8n": "n8n",
  "make.com": "Make.com",
  "claude-api": "Claude AI",
  "hubspot": "HubSpot",
  "healthcare": "Healthcare",
  "ai-classification": "AI Classification",
  "web-scraping": "Web Scraping",
  "google-sheets": "Google Sheets",
  "webhooks": "Webhooks",
  "gdpr": "GDPR",
  "slack": "Slack",
  "calendly": "Calendly",
  "hitl": "Human-in-the-Loop",
  "news-filtering": "News Filtering",
  "document-processing": "Document Processing",
  "mollie": "Mollie",
  "google-drive": "Google Drive",
};

const colorByIndex = ["blue", "purple", "green", "orange"] as const;

export default function WorkPage() {
  const projects = getDisplayableProposals();

  const industries = [...new Set(
    projects.flatMap((p) =>
      p.frontmatter.tags.filter((t) =>
        ["healthcare", "finance", "media", "pr"].includes(t.toLowerCase())
      )
    )
  )];

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Portfolio
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Our Work
          </h1>
          <p className="mt-4 max-w-xl mx-auto text-lg leading-relaxed text-muted">
            Automation systems built for real businesses. Each project includes
            a detailed proposal, architecture design, and full implementation.
          </p>
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-y border-border">
        <div className="mx-auto max-w-3xl px-6 py-8">
          <div className="grid grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-2xl font-bold text-accent">{projects.length}</div>
              <div className="text-xs text-muted">Projects</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent">{industries.length + 2}</div>
              <div className="text-xs text-muted">Industries</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent">3</div>
              <div className="text-xs text-muted">Orchestrators</div>
            </div>
          </div>
        </div>
      </section>

      {/* Projects grid */}
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="grid gap-8">
          {projects.map((project, i) => {
            const fm = project.frontmatter;
            const color = colorByIndex[i % colorByIndex.length];
            const orchestrator = fm.tags.find((t) =>
              ["n8n", "make.com", "trigger.dev"].includes(t)
            );
            const techTags = fm.tags.filter(
              (t) => !["automation", "crm", orchestrator].includes(t)
            );

            return (
              <Link
                key={fm.slug}
                href={`/proposals/${fm.slug}`}
                className="group grid gap-6 rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-md sm:grid-cols-3"
              >
                {/* Left: project info */}
                <div className="sm:col-span-2">
                  <div className="mb-1 flex items-center gap-3">
                    <span className="text-xs font-medium uppercase tracking-wider text-muted">
                      {fm.prospect}
                    </span>
                    {orchestrator && (
                      <span className={`rounded-full bg-${color}-bg px-2.5 py-0.5 text-xs font-medium text-${color}`}>
                        {tagLabels[orchestrator] || orchestrator}
                      </span>
                    )}
                  </div>
                  <h2 className="mb-2 text-xl font-bold group-hover:text-accent transition-colors">
                    {fm.project_title}
                  </h2>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {techTags.slice(0, 5).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted"
                      >
                        {tagLabels[tag] || tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Right: meta */}
                <div className="flex flex-col gap-2 text-sm text-muted sm:items-end sm:text-right">
                  <div>
                    <span className="text-xs uppercase tracking-wider">Timeline</span>
                    <div className="font-medium text-foreground">{fm.timeline}</div>
                  </div>
                  <div>
                    <span className="text-xs uppercase tracking-wider">Source</span>
                    <div className="font-medium text-foreground capitalize">{fm.source}</div>
                  </div>
                  <div className="mt-auto text-xs font-medium text-accent group-hover:text-accent-light transition-colors">
                    View proposal &rarr;
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-2xl font-bold tracking-tight">
            Have a similar project?
          </h2>
          <p className="text-muted">
            Tell us about your workflow and we&rsquo;ll scope out a solution.
          </p>
          <Link
            href="/contact"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Start a Conversation
          </Link>
        </div>
      </section>
    </div>
  );
}
