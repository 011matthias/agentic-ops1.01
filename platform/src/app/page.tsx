import Link from "next/link";

const services = [
  {
    title: "Lead & Inquiry Automation",
    description:
      "Instant auto-responses, AI-personalized follow-up sequences, multi-factor lead scoring, and smart routing to your team.",
  },
  {
    title: "CRM & ERP Integration",
    description:
      "Bidirectional sync between your CRM and ERP. Deal notifications, automated invoicing, and status-driven workflows.",
  },
  {
    title: "Sales Campaign Operations",
    description:
      "Campaign dashboards, data aggregation, AI sentiment scoring on replies, and weekly trend tracking across your tools.",
  },
  {
    title: "Custom Workflow Automation",
    description:
      "Database polling, data enrichment pipelines, task intelligence, and any SaaS-to-SaaS connection you need.",
  },
];

const stats = [
  { value: "20+", label: "Integrations" },
  { value: "3", label: "Orchestrators" },
  { value: "24/7", label: "Uptime" },
];

export default function Home() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-6 py-24 text-center sm:py-32">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          We build automations that run your business
        </h1>
        <p className="max-w-xl text-lg leading-relaxed text-muted">
          Lead follow-up, CRM sync, sales dashboards, and custom workflows
          &mdash; connected to your existing tools, running on autopilot.
        </p>
        <div className="flex gap-4">
          <Link
            href="/contact"
            className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
          >
            Get in Touch
          </Link>
          <Link
            href="/services"
            className="rounded-full border border-border px-6 py-3 text-sm font-medium transition-colors hover:bg-border/30"
          >
            See Services
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border">
        <div className="mx-auto flex max-w-3xl justify-center divide-x divide-border px-6 py-8">
          {stats.map((stat) => (
            <div key={stat.label} className="flex flex-col items-center px-10">
              <span className="text-2xl font-bold">{stat.value}</span>
              <span className="text-sm text-muted">{stat.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Services overview */}
      <section className="mx-auto max-w-4xl px-6 py-20">
        <h2 className="mb-4 text-center text-2xl font-semibold tracking-tight">
          What we automate
        </h2>
        <p className="mb-12 text-center text-muted">
          Every business has repetitive workflows. We turn them into reliable,
          always-on systems.
        </p>
        <div className="grid gap-8 sm:grid-cols-2">
          {services.map((service) => (
            <div
              key={service.title}
              className="rounded-lg border border-border p-6"
            >
              <h3 className="mb-2 font-semibold">{service.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {service.description}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <Link
            href="/services"
            className="text-sm font-medium text-accent hover:text-accent-light"
          >
            Learn more about our services &rarr;
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">
            Ready to automate?
          </h2>
          <p className="text-muted">
            Tell us about your workflow. We&rsquo;ll show you what&rsquo;s
            possible.
          </p>
          <Link
            href="/contact"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
          >
            Start a Conversation
          </Link>
        </div>
      </section>
    </div>
  );
}
