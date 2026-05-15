import type { Metadata } from "next";
import Link from "next/link";
import { marketplaceItems, customItems } from "@/content/catalog";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "Automation Marketplace - UnpauseAI",
  description:
    "Battle-tested automation workflows from real projects. Self-service blueprints or we implement for you. Lead follow-up, CRM sync, AI classification, database polling, and more.",
};

const zones = [
  {
    color: "blue" as const,
    title: "Data In",
    subtitle: "Capture and ingest",
    items: [
      "Webhook listeners",
      "Database polling",
      "Form submissions",
      "API ingestion",
      "Email parsing",
    ],
  },
  {
    color: "purple" as const,
    title: "Processing",
    subtitle: "Transform and decide",
    items: [
      "AI classification",
      "Data enrichment",
      "Routing logic",
      "Validation rules",
      "Human-in-the-loop gates",
    ],
  },
  {
    color: "green" as const,
    title: "Output",
    subtitle: "Act and notify",
    items: [
      "Email sequences",
      "CRM updates",
      "Slack notifications",
      "Report generation",
      "Dashboard feeds",
    ],
  },
];

const zoneStyles = {
  blue: "border-blue/30 bg-gradient-to-br from-blue-bg to-transparent",
  purple: "border-purple/30 bg-gradient-to-br from-purple-bg to-transparent",
  green: "border-green/30 bg-gradient-to-br from-green-bg to-transparent",
} as const;

const zoneTitleStyles = {
  blue: "text-blue",
  purple: "text-purple",
  green: "text-green",
} as const;

const zoneDotStyles = {
  blue: "bg-blue",
  purple: "bg-purple",
  green: "bg-green",
} as const;

const tools = [
  "Make.com",
  "n8n",
  "Trigger.dev",
  "Claude API",
  "Google Sheets",
  "HubSpot",
  "Slack",
  "Gmail",
  "MySQL",
  "Postgres",
  "Fortnox",
  "Pipedrive",
];

export default function WorkPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Automation Marketplace
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Battle-tested workflows
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Every automation here was built for a real project, tested with real
            data, and refined until it stayed done. Buy the blueprint or let us
            implement it for you.
          </p>
        </div>
      </section>

      {/* Assessment Banner */}
      <ScrollReveal>
        <section className="border-y border-border bg-gradient-to-r from-blue-bg/50 via-purple-bg/30 to-blue-bg/50">
          <div className="mx-auto flex max-w-4xl flex-col items-center gap-3 px-6 py-8 text-center sm:flex-row sm:justify-between sm:text-left">
            <div>
              <p className="font-semibold">Not sure which automation fits?</p>
              <p className="text-sm text-muted">
                Get a personalized assessment of what we&rsquo;d build for your workflow.
              </p>
            </div>
            <Link
              href="/assessment"
              className="shrink-0 rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Request Assessment
            </Link>
          </div>
        </section>
      </ScrollReveal>

      {/* Marketplace Products */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 py-20">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
              Marketplace
            </span>
            <h2 className="text-3xl font-bold tracking-tight">
              Ready-to-deploy automations
            </h2>
            <p className="mt-3 text-muted">
              Two options for each: self-service blueprint or full implementation by our team.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {marketplaceItems.map((item) => (
              <div
                key={item.id}
                className="flex flex-col rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-lg"
              >
                {/* Category tag */}
                <span className="mb-3 inline-block self-start rounded-full bg-blue-bg px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-blue">
                  {item.category}
                </span>

                <h3 className="mb-1 text-lg font-bold">{item.name}</h3>
                <p className="mb-4 text-sm leading-relaxed text-muted">
                  {item.tagline}
                </p>

                {/* Tier options */}
                <div className="mt-auto space-y-3 border-t border-border pt-4">
                  <div>
                    <span className="text-xs font-medium text-muted">Self-service</span>
                    <p className="text-xs text-muted">Blueprint + docs</p>
                  </div>
                  <div className="rounded-lg bg-accent/5 px-3 py-2">
                    <span className="text-xs font-semibold text-accent">Premium</span>
                    <p className="text-xs text-muted">We implement it</p>
                  </div>
                </div>

                {/* Tools */}
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {item.tools.map((tool) => (
                    <span
                      key={tool}
                      className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* Custom Work */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-4xl px-6 py-20">
            <div className="mb-10 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Custom Solutions
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                Need something specific?
              </h2>
              <p className="mt-3 text-muted">
                For workflows that don&rsquo;t fit a template. Fully scoped, fully built, fully yours.
              </p>
            </div>
            {customItems.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border-l-4 border-l-accent bg-gradient-to-r from-blue-bg/50 to-transparent border border-border p-6"
              >
                <div className="mb-1 text-sm font-bold text-accent">Premium engagement</div>
                <h3 className="mb-2 text-xl font-bold">{item.name}</h3>
                <p className="mb-4 text-sm leading-relaxed text-muted">
                  {item.description}
                </p>
                <ul className="grid gap-2 sm:grid-cols-2">
                  {item.premiumIncludes.map((point) => (
                    <li
                      key={point}
                      className="flex items-start gap-2 text-sm text-muted"
                    >
                      <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* Zone Architecture */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-4xl px-6 py-20">
            <div className="mb-10 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Architecture
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                How every automation works
              </h2>
              <p className="mt-3 text-muted">
                Three layers. One reliable pattern.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {zones.map((zone) => (
                <div
                  key={zone.title}
                  className={`rounded-xl border p-5 transition-all hover:-translate-y-0.5 ${zoneStyles[zone.color]}`}
                >
                  <div className={`text-sm font-bold ${zoneTitleStyles[zone.color]}`}>
                    {zone.title}
                  </div>
                  <div className="mb-3 text-xs text-muted">{zone.subtitle}</div>
                  <ul className="space-y-1.5">
                    {zone.items.map((item) => (
                      <li key={item} className="flex items-center gap-2 text-sm">
                        <span
                          className={`inline-block h-1.5 w-1.5 rounded-full ${zoneDotStyles[zone.color]}`}
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Tools strip */}
      <section className="border-y border-border">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <p className="mb-6 text-center text-xs font-semibold uppercase tracking-wider text-muted">
            Tools &amp; Integrations
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {tools.map((tool) => (
              <span
                key={tool}
                className="rounded-full border border-border bg-surface px-4 py-1.5 text-xs font-medium text-muted transition-colors hover:text-foreground"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Have a workflow to automate?
          </h2>
          <p className="text-muted">
            Describe it. We&rsquo;ll tell you what&rsquo;s possible within 24 hours.
          </p>
          <Link
            href="/assessment"
            className="mt-2 rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request Assessment
          </Link>
        </div>
      </section>
    </div>
  );
}
