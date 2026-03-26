import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description:
    "UnpauseAI builds custom automation solutions. We connect your existing tools into reliable workflows that run 24/7.",
};

const orchestrators = [
  {
    name: "Make.com",
    description: "Visual workflow automation for complex multi-step processes",
    color: "blue" as const,
  },
  {
    name: "n8n",
    description: "Self-hosted workflow engine for data-heavy integrations",
    color: "purple" as const,
  },
  {
    name: "Trigger.dev",
    description: "Code-first automation for custom logic and AI workflows",
    color: "green" as const,
  },
];

const colorStyles = {
  blue: { border: "border-l-blue", bg: "bg-blue-bg", text: "text-blue" },
  purple: { border: "border-l-purple", bg: "bg-purple-bg", text: "text-purple" },
  green: { border: "border-l-green", bg: "bg-green-bg", text: "text-green" },
};

const processSteps = [
  { step: "01", title: "Discovery", description: "We learn your tools, your pain points, and your workflow gaps.", color: "blue" as const },
  { step: "02", title: "Proposal", description: "Detailed scope, architecture diagram, timeline, and investment breakdown.", color: "purple" as const },
  { step: "03", title: "Build & Test", description: "We build with real data, test every path, and iterate until it works.", color: "green" as const },
  { step: "04", title: "Handoff", description: "You own the system. Documentation, monitoring, and independent operation.", color: "orange" as const },
];

const stepColors = {
  blue: { circle: "bg-blue text-white", line: "bg-blue/20" },
  purple: { circle: "bg-purple text-white", line: "bg-purple/20" },
  green: { circle: "bg-green text-white", line: "bg-green/20" },
  orange: { circle: "bg-orange text-white", line: "bg-orange/20" },
};

export default function AboutPage() {
  return (
    <div className="flex flex-col">
      <section className="mx-auto max-w-3xl px-6 py-20">
        <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
          Who We Are
        </span>
        <h1 className="mb-6 text-3xl font-extrabold tracking-tight sm:text-4xl">
          About UnpauseAI
        </h1>

        <div className="space-y-6 leading-relaxed text-muted">
          <p>
            We&rsquo;re an automation consultancy that builds workflows for
            businesses. Not the &ldquo;let&rsquo;s replace your whole
            stack&rdquo; kind. We connect the tools you already use and make
            them work together without you having to think about it.
          </p>
          <p>
            Our clients are businesses that deal with high volumes of repetitive
            work: lead follow-up, CRM-to-ERP sync, campaign reporting, invoice
            generation. The kind of tasks that someone on the team is doing
            manually today, and that could be running on autopilot instead.
          </p>
          <p>
            We scope every project with a detailed proposal, build it using
            proven orchestration platforms, test it with real data, and hand it
            off as an independent system you own. No lock-in, no ongoing
            dependency.
          </p>
        </div>
      </section>

      {/* How we work */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
            Process
          </span>
          <h2 className="mb-2 text-xl font-bold">How we work</h2>
          <p className="mb-10 text-muted">
            Four phases from first conversation to independent operation.
          </p>

          <div className="grid gap-6 sm:grid-cols-2">
            {processSteps.map((item) => {
              const sc = stepColors[item.color];
              return (
                <div
                  key={item.step}
                  className="flex gap-4 rounded-xl border border-border bg-surface p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
                >
                  <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full ${sc.circle} text-sm font-bold`}>
                    {item.step}
                  </div>
                  <div>
                    <h3 className="mb-1 font-semibold">{item.title}</h3>
                    <p className="text-sm text-muted">{item.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Orchestrators */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
            Technology
          </span>
          <h2 className="mb-2 text-xl font-bold">Our approach</h2>
          <p className="mb-8 text-muted">
            We pick the right tool for the job, not the tool we know best.
          </p>

          <div className="grid gap-6 sm:grid-cols-3">
            {orchestrators.map((orch) => {
              const styles = colorStyles[orch.color];
              return (
                <div
                  key={orch.name}
                  className={`rounded-xl border border-border ${styles.border} border-l-4 ${styles.bg} p-5 transition-all hover:-translate-y-0.5`}
                >
                  <h3 className={`mb-1 font-semibold ${styles.text}`}>{orch.name}</h3>
                  <p className="text-sm text-muted">{orch.description}</p>
                </div>
              );
            })}
          </div>

          <p className="mt-8 text-sm text-muted">
            We integrate with services like HubSpot, Fortnox, Smartlead,
            Google Sheets, Gmail, Slack, Airtable, MySQL, Postgres, OpenAI,
            and more.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-16 text-center">
          <h2 className="text-xl font-bold">Want to work together?</h2>
          <p className="text-muted">
            Tell us about the workflow you want to automate.
          </p>
          <Link
            href="/contact"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Get in Touch
          </Link>
        </div>
      </section>
    </div>
  );
}
