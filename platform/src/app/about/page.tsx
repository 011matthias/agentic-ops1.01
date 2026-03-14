import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description:
    "UnpausAI builds custom automation solutions. We connect your existing tools into reliable workflows that run 24/7.",
};

const orchestrators = [
  {
    name: "Make.com",
    description: "Visual workflow automation for complex multi-step processes",
  },
  {
    name: "n8n",
    description: "Self-hosted workflow engine for data-heavy integrations",
  },
  {
    name: "Trigger.dev",
    description: "Code-first automation for custom logic and AI workflows",
  },
];

export default function AboutPage() {
  return (
    <div className="flex flex-col">
      <section className="mx-auto max-w-3xl px-6 py-20">
        <h1 className="mb-6 text-3xl font-bold tracking-tight sm:text-4xl">
          About UnpausAI
        </h1>

        <div className="space-y-6 leading-relaxed text-muted">
          <p>
            We&rsquo;re an automation consultancy that builds workflows for
            businesses. Not the &ldquo;let&rsquo;s replace your whole
            stack&rdquo; kind &mdash; the kind that connects the tools you
            already use and makes them work together without you having to think
            about it.
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

      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <h2 className="mb-2 text-xl font-semibold">Our approach</h2>
          <p className="mb-8 text-muted">
            We pick the right tool for the job, not the tool we know best.
          </p>

          <div className="grid gap-6 sm:grid-cols-3">
            {orchestrators.map((orch) => (
              <div
                key={orch.name}
                className="rounded-lg border border-border p-5"
              >
                <h3 className="mb-1 font-medium">{orch.name}</h3>
                <p className="text-sm text-muted">{orch.description}</p>
              </div>
            ))}
          </div>

          <p className="mt-8 text-sm text-muted">
            We also integrate with 20+ external services: HubSpot, Fortnox,
            Smartlead, Google Sheets, Gmail, Slack, Airtable, MySQL, Postgres,
            OpenAI, and more.
          </p>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-16 text-center">
          <h2 className="text-xl font-semibold">Want to work together?</h2>
          <p className="text-muted">
            Tell us about the workflow you want to automate.
          </p>
          <Link
            href="/contact"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
          >
            Get in Touch
          </Link>
        </div>
      </section>
    </div>
  );
}
