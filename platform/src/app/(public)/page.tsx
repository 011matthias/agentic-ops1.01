import Link from "next/link";
import Card from "@/components/ui/Card";

const iconStyles = {
  blue: "bg-blue/10 text-blue",
  purple: "bg-purple/10 text-purple",
  green: "bg-green/10 text-green",
  orange: "bg-orange/10 text-orange",
} as const;

const orchStyles = {
  blue: "border-blue/20 bg-blue-bg text-blue",
  purple: "border-purple/20 bg-purple-bg text-purple",
  green: "border-green/20 bg-green-bg text-green",
} as const;

const services = [
  {
    title: "Lead & Inquiry Automation",
    description:
      "Instant auto-responses, AI-personalized follow-up sequences, multi-factor lead scoring, and smart routing to your team.",
    color: "blue" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
        <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
      </svg>
    ),
  },
  {
    title: "CRM & ERP Integration",
    description:
      "Bidirectional sync between your CRM and ERP. Deal notifications, automated invoicing, and status-driven workflows.",
    color: "purple" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    title: "Sales Campaign Operations",
    description:
      "Campaign dashboards, data aggregation, AI sentiment scoring on replies, and weekly trend tracking across your tools.",
    color: "green" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    title: "Custom Workflow Automation",
    description:
      "Database polling, data enrichment pipelines, task intelligence, and any SaaS-to-SaaS connection you need.",
    color: "orange" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
      </svg>
    ),
  },
];

const orchestrators = [
  { name: "Make.com", description: "Visual workflow automation", color: "blue" as const },
  { name: "n8n", description: "Self-hosted data pipelines", color: "purple" as const },
  { name: "Trigger.dev", description: "Code-first AI workflows", color: "green" as const },
];

const stats = [
  { value: "3", label: "Orchestrators" },
  { value: "10+", label: "Integrations" },
  { value: "24/7", label: "Always On" },
];

export default function Home() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,var(--color-border)_1px,transparent_0)] bg-[length:24px_24px] opacity-40" />
        <div className="relative mx-auto flex max-w-3xl flex-col items-center gap-6 px-6 py-24 text-center sm:py-32">
          <span className="inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Automation Infrastructure
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            We build automations that run your business
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-muted">
            Lead follow-up, CRM sync, sales dashboards, and custom workflows.
            Connected to your existing tools, running on autopilot.
          </p>
          <div className="flex gap-4">
            <Link
              href="/contact"
              className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Get in Touch
            </Link>
            <Link
              href="/services"
              className="rounded-full border border-border px-6 py-3 text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
            >
              See Services
            </Link>
          </div>

          {/* Stat cards */}
          <div className="mt-4 grid w-full max-w-md grid-cols-3 gap-4">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-xl border border-border bg-surface px-4 py-3 text-center"
              >
                <div className="text-xl font-bold text-accent">{stat.value}</div>
                <div className="text-xs text-muted">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services overview */}
      <section className="mx-auto max-w-4xl px-6 py-20">
        <div className="mb-12 text-center">
          <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
            Capabilities
          </span>
          <h2 className="text-2xl font-bold tracking-tight">
            What we automate
          </h2>
          <p className="mt-3 text-muted">
            Every business has repetitive workflows. We turn them into reliable,
            always-on systems.
          </p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          {services.map((service) => (
            <Card key={service.title} color={service.color}>
              <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg ${iconStyles[service.color]}`}>
                {service.icon}
              </div>
              <h3 className="mb-2 font-semibold">{service.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {service.description}
              </p>
            </Card>
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

      {/* Orchestrators */}
      <section className="border-y border-border">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <p className="mb-8 text-center text-xs font-semibold uppercase tracking-wider text-muted">
            Built on proven platforms
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {orchestrators.map((orch) => (
              <div
                key={orch.name}
                className={`flex flex-col items-center gap-1 rounded-xl border ${orchStyles[orch.color]} px-6 py-4 text-center transition-all hover:-translate-y-0.5`}
              >
                <span className="text-sm font-bold">{orch.name}</span>
                <span className="text-xs text-muted">{orch.description}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-2xl font-bold tracking-tight">
            Ready to automate?
          </h2>
          <p className="text-muted">
            Tell us about your workflow. We&rsquo;ll show you what&rsquo;s
            possible.
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
