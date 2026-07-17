import type { Metadata } from "next";
import Link from "next/link";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "Compare Automation Options",
  description:
    "How UnpauseAI compares to hiring freelancers, using agencies, or building automation in-house. Honest trade-offs for each approach.",
};

const approaches = [
  {
    name: "DIY / In-House",
    color: "orange" as const,
    summary: "Your team builds and maintains the automations using no-code tools or custom scripts.",
    pros: [
      "Full control over timeline and priorities",
      "Deep understanding of your own business logic",
      "No external dependency",
      "Lowest cost if you already have the skills",
    ],
    cons: [
      "Requires dedicated technical time from your team",
      "Learning curve for Make.com, n8n, or similar platforms",
      "No external review means blind spots in error handling",
      "Maintenance burden stays with your team forever",
      "Opportunity cost: your engineers could be building product",
    ],
    bestFor: "Small teams with technical founders who have time to build and maintain automations themselves.",
  },
  {
    name: "Freelancer",
    color: "purple" as const,
    summary: "You hire an individual contractor to build your automation, typically found on Upwork or similar platforms.",
    pros: [
      "Lower hourly rates than agencies",
      "Direct communication, no account managers",
      "Flexible scheduling",
      "Can find specialists for specific platforms",
    ],
    cons: [
      "Quality varies wildly, hard to vet upfront",
      "Single point of failure (sick, busy, disappears)",
      "Often no structured testing or documentation",
      "Scope creep is common with hourly billing",
      "Limited experience with production-grade error handling",
      "Handoff quality depends entirely on the individual",
    ],
    bestFor: "Simple, one-off automations where the risk of failure is low and you can manage the freelancer closely.",
  },
  {
    name: "Traditional Agency",
    color: "blue" as const,
    summary: "A larger automation or consulting firm builds your workflows, typically with account managers and junior developers.",
    pros: [
      "Team capacity for larger projects",
      "Established processes and project management",
      "Broader platform expertise",
      "Ongoing support contracts available",
    ],
    cons: [
      "Higher cost (overhead for PMs, sales, offices)",
      "You talk to account managers, not the person building it",
      "Junior developers often do the actual work",
      "Long sales cycles and proposal processes",
      "Vendor lock-in is common (they keep the keys)",
      "Cookie-cutter solutions that don't fit your workflow",
    ],
    bestFor: "Large enterprises with budget for managed services and complex, multi-department automation programs.",
  },
  {
    name: "UnpauseAI",
    color: "green" as const,
    summary: "Specialized automation consultancy. Fixed-scope projects with full testing, documentation, and ownership transfer.",
    pros: [
      "Fixed price, defined scope before work begins",
      "You own everything: accounts, code, credentials",
      "Tested with your real production data",
      "Built-in error handling and alerting",
      "Full documentation for your team to maintain it",
      "30-day post-launch support included",
      "Platform-agnostic: we pick the right tool for the job",
      "Direct access to the person building your automation",
    ],
    cons: [
      "Small team: capacity is limited",
      "EU-based: CET timezone may not overlap with yours",
      "Not the cheapest option for simple tasks",
      "We say no to projects that don't fit our model",
    ],
    bestFor: "Businesses that need reliable, production-grade automation and want to own the result. Especially those in regulated industries or handling high volumes.",
  },
];

const approachColors = {
  blue: { badge: "bg-blue-bg text-blue", border: "border-t-blue", ring: "ring-blue/20" },
  purple: { badge: "bg-purple-bg text-purple", border: "border-t-purple", ring: "ring-purple/20" },
  green: { badge: "bg-green-bg text-green", border: "border-t-green", ring: "ring-green/20" },
  orange: { badge: "bg-orange-bg text-orange", border: "border-t-orange", ring: "ring-orange/20" },
};

const comparisonRows = [
  {
    dimension: "Pricing model",
    diy: "Your team's time",
    freelancer: "Hourly (typically $30-80/hr)",
    agency: "Project-based or retainer ($5K-50K+)",
    us: "Fixed price ($99-2,500+)",
  },
  {
    dimension: "Timeline",
    diy: "Depends on your team's availability",
    freelancer: "1-4 weeks for simple automations",
    agency: "4-12 weeks (includes sales cycle)",
    us: "1-7 weeks (no sales cycle overhead)",
  },
  {
    dimension: "You own the result",
    diy: "Yes",
    freelancer: "Usually, but verify",
    agency: "Often not (vendor lock-in)",
    us: "Always",
  },
  {
    dimension: "Error handling",
    diy: "If you build it",
    freelancer: "Inconsistent",
    agency: "Varies by team",
    us: "Built into every project",
  },
  {
    dimension: "Documentation",
    diy: "If you write it",
    freelancer: "Rarely included",
    agency: "Usually generic templates",
    us: "Custom docs for your workflow",
  },
  {
    dimension: "Post-launch support",
    diy: "Your team handles it",
    freelancer: "Ends when the contract ends",
    agency: "Paid retainer",
    us: "30 days included free",
  },
  {
    dimension: "Testing with real data",
    diy: "If you do it",
    freelancer: "Usually demo data only",
    agency: "Varies",
    us: "Always with production data",
  },
  {
    dimension: "Platform choice",
    diy: "Whatever you know",
    freelancer: "Whatever they know",
    agency: "Their preferred stack",
    us: "Best fit for your workflow",
  },
];

export default function ComparePage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Compare
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            How should you get your automation built?
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            There are four ways to automate your workflows. Each has real
            trade-offs. Here&rsquo;s an honest comparison.
          </p>
        </div>
      </section>

      {/* Approach Cards */}
      <ScrollReveal>
        <section className="mx-auto max-w-6xl px-6 pb-20">
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {approaches.map((approach) => {
              const colors = approachColors[approach.color];
              const isUs = approach.name === "UnpauseAI";
              return (
                <div
                  key={approach.name}
                  className={`flex flex-col rounded-xl border ${isUs ? "border-2 border-accent shadow-lg" : "border-border"} border-t-4 ${colors.border} bg-surface p-6 transition-all hover:-translate-y-0.5 ${isUs ? "hover:shadow-xl" : "hover:shadow-md"}`}
                >
                  {isUs && (
                    <span className="mb-3 inline-block self-start rounded-full bg-accent px-3 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
                      Our approach
                    </span>
                  )}
                  <h3 className="mb-2 text-lg font-bold">{approach.name}</h3>
                  <p className="mb-5 text-sm leading-relaxed text-muted">
                    {approach.summary}
                  </p>

                  <div className="mb-4">
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-green">
                      Strengths
                    </h4>
                    <ul className="space-y-1.5">
                      {approach.pros.map((pro) => (
                        <li key={pro} className="flex items-start gap-2 text-xs leading-relaxed text-muted">
                          <svg className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          {pro}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mb-5">
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-orange">
                      Trade-offs
                    </h4>
                    <ul className="space-y-1.5">
                      {approach.cons.map((con) => (
                        <li key={con} className="flex items-start gap-2 text-xs leading-relaxed text-muted">
                          <svg className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          {con}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-auto rounded-lg bg-surface-hover p-3">
                    <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted">
                      Best for
                    </h4>
                    <p className="text-xs leading-relaxed text-muted">{approach.bestFor}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </ScrollReveal>

      {/* Comparison Table */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Side by Side
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                Feature comparison
              </h2>
            </div>

            <div className="overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface">
                    <th className="px-5 py-4 text-left font-semibold"></th>
                    <th className="px-5 py-4 text-left font-semibold text-orange">DIY</th>
                    <th className="px-5 py-4 text-left font-semibold text-purple">Freelancer</th>
                    <th className="px-5 py-4 text-left font-semibold text-blue">Agency</th>
                    <th className="px-5 py-4 text-left font-semibold text-accent">UnpauseAI</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((row) => (
                    <tr key={row.dimension} className="border-b border-border transition-colors hover:bg-surface-hover">
                      <td className="px-5 py-3.5 font-medium">{row.dimension}</td>
                      <td className="px-5 py-3.5 text-muted">{row.diy}</td>
                      <td className="px-5 py-3.5 text-muted">{row.freelancer}</td>
                      <td className="px-5 py-3.5 text-muted">{row.agency}</td>
                      <td className="px-5 py-3.5 font-medium">{row.us}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* When NOT to choose us */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-3xl px-6 py-20">
            <div className="mb-10 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Honest Take
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                When we&rsquo;re not the right fit
              </h2>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="mb-1 font-semibold">You need a full-time automation engineer</h3>
                <p className="text-sm text-muted">
                  If you need someone continuously building and iterating on
                  automations week after week, a full-time hire or internal team
                  is more cost-effective than project-based work. We build
                  discrete systems, not ongoing capacity.
                </p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="mb-1 font-semibold">The task is a quick Zapier connection</h3>
                <p className="text-sm text-muted">
                  If you just need &ldquo;when a form is submitted, add a row to
                  a spreadsheet,&rdquo; you don&rsquo;t need us. Zapier or Make.com&rsquo;s
                  free tier handles that in 10 minutes. We focus on workflows
                  where reliability, error handling, and data integrity matter.
                </p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="mb-1 font-semibold">Budget is under $500</h3>
                <p className="text-sm text-muted">
                  Our self-service blueprints start at $99, but custom work
                  starts at EUR 2,500. For smaller budgets, our blog posts and
                  blueprint documentation may be enough to build it yourself.
                </p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="mb-1 font-semibold">You need a US-timezone team</h3>
                <p className="text-sm text-muted">
                  We&rsquo;re based in Germany (CET). We work asynchronously with
                  clients worldwide, but if you need real-time collaboration
                  during US business hours, the timezone gap may be a friction
                  point.
                </p>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* CTA */}
      <section className="border-t border-border bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Think we might be the right fit?
          </h2>
          <p className="max-w-lg text-muted">
            Describe your workflow. We&rsquo;ll tell you honestly whether we&rsquo;re
            the right option, and if not, which approach we&rsquo;d recommend instead.
          </p>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/assessment"
              className="rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Get Your $1 Assessment
            </Link>
            <Link
              href="/pricing"
              className="rounded-full border border-border px-7 py-3 text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
