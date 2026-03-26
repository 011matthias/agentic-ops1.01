import type { Metadata } from "next";
import Link from "next/link";
import { readyItems, customItems } from "@/content/catalog";

export const metadata: Metadata = {
  title: "What We Build - UnpauseAI",
  description:
    "Automation templates and custom solutions: lead follow-up, CRM sync, reporting, webhook routing, database polling, and more.",
};

const zones = [
  {
    color: "blue" as const,
    icon: "\u{1F4E5}",
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
    icon: "\u{2699}\u{FE0F}",
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
    icon: "\u{1F4E4}",
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
  blue: "border-blue/30 bg-blue-bg",
  purple: "border-purple/30 bg-purple-bg",
  green: "border-green/30 bg-green-bg",
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
  "Google Sheets",
  "HubSpot",
  "Slack",
  "Gmail",
  "OpenAI",
  "MySQL",
  "Postgres",
];

export default function WorkPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Automation Library
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            What We Build
          </h1>
          <p className="mt-4 max-w-xl mx-auto text-lg leading-relaxed text-muted">
            Ready-made automation templates and custom solutions.
            Every system follows the same pattern: ingest data, process it
            intelligently, and deliver the right output.
          </p>
        </div>
      </section>

      {/* Zone Cards */}
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-10 text-center">
          <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
            Architecture
          </span>
          <h2 className="text-2xl font-bold tracking-tight">
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
              <div className="mb-2 text-2xl">{zone.icon}</div>
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
      </section>

      {/* Solution Grid */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <div className="mb-10 text-center">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
              Templates
            </span>
            <h2 className="text-2xl font-bold tracking-tight">
              Ready-made automations
            </h2>
            <p className="mt-3 text-muted">
              Pre-built systems you can deploy immediately. Each includes setup,
              documentation, and 30 days of support.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {readyItems.map((item, i) => (
              <div
                key={item.id}
                className="group flex gap-4 rounded-xl border border-border bg-surface p-4 transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-bg text-xs font-bold text-blue">
                  {i + 1}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-sm">{item.name}</div>
                  <div className="mt-0.5 text-xs leading-relaxed text-muted">
                    {item.tagline}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
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
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Custom + Audit */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <div className="mb-10 text-center">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
              Custom Solutions
            </span>
            <h2 className="text-2xl font-bold tracking-tight">
              Need something specific?
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {customItems.map((item) => {
              const isAudit = item.slug === "automation-audit";
              const borderColor = isAudit
                ? "border-l-green"
                : "border-l-blue";
              const bgColor = isAudit ? "bg-green-bg/50" : "bg-blue-bg/50";
              const accentColor = isAudit ? "text-green" : "text-blue";

              return (
                <div
                  key={item.id}
                  className={`rounded-r-xl rounded-l border-l-4 ${borderColor} ${bgColor} p-5`}
                >
                  <div
                    className={`mb-1 text-xs font-bold uppercase tracking-wider ${accentColor}`}
                  >
                    {item.startingFrom}
                  </div>
                  <h3 className="mb-2 font-bold">{item.name}</h3>
                  <p className="mb-3 text-sm leading-relaxed text-muted">
                    {item.description}
                  </p>
                  <ul className="space-y-1">
                    {item.whatYouGet.slice(0, 3).map((point) => (
                      <li
                        key={point}
                        className="flex items-start gap-2 text-xs text-muted"
                      >
                        <span className="mt-1 inline-block h-1 w-1 shrink-0 rounded-full bg-muted" />
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      </section>

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
          <h2 className="text-2xl font-bold tracking-tight">
            Have a workflow to automate?
          </h2>
          <p className="text-muted">
            Tell us what you&rsquo;re doing manually. We&rsquo;ll tell you
            what&rsquo;s possible.
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
