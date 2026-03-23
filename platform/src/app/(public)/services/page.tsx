import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Services",
  description:
    "Automation services: lead follow-up, CRM/ERP integration, sales campaign operations, and custom workflow automation.",
};

const services = [
  {
    title: "Lead & Inquiry Automation",
    description:
      "Your forms get submitted. Then what? We build the system that responds instantly, scores each lead across multiple factors, routes hot prospects to your team, and follows up automatically until they reply.",
    features: [
      "Instant auto-response to form submissions",
      "AI-personalized follow-up sequences",
      "Multi-factor lead scoring and priority routing",
      "Reply detection with automatic sequence stopping",
      "A/B testing across email variants",
    ],
    how: "Form submitted \u2192 Lead scored & logged \u2192 Personalized response sent \u2192 Follow-up sequence activated \u2192 Reply detected \u2192 Team notified",
    tools: ["Make.com", "Gmail", "Google Sheets", "OpenAI", "MySQL"],
  },
  {
    title: "CRM & ERP Integration",
    description:
      "Your CRM and ERP should talk to each other without you copying data between them. We build bidirectional syncs, automated invoicing, and deal-stage workflows that keep everything in lockstep.",
    features: [
      "Bidirectional sync between CRM and ERP",
      "Deal stage notifications via Slack or email",
      "Automated invoicing on status changes",
      "Order approval workflows",
      "Customer data deduplication",
    ],
    how: "Deal stage changes \u2192 Data synced to ERP \u2192 Invoice generated \u2192 Team notified \u2192 Records updated",
    tools: ["n8n", "HubSpot", "Fortnox", "Upsales", "TeamLeader", "Slack"],
  },
  {
    title: "Sales Campaign Operations",
    description:
      "Campaign data lives in too many places. We aggregate it into dashboards, score incoming replies with AI, and give you weekly trend reports so you know what\u2019s working.",
    features: [
      "Campaign data aggregation dashboards",
      "AI sentiment scoring on email replies",
      "Weekly trend snapshots and historical tracking",
      "Multi-source data visualization",
      "Custom API endpoints for your frontend",
    ],
    how: "Campaign data pulled \u2192 Aggregated in sheets \u2192 Dashboard updated \u2192 Trends calculated \u2192 Reports delivered",
    tools: ["n8n", "Smartlead", "Google Sheets", "OpenRouter"],
  },
  {
    title: "Custom Workflow Automation",
    description:
      "If it\u2019s repetitive and involves moving data between systems, we can automate it. Database polling, data enrichment pipelines, scheduled reports, webhook processing \u2014 whatever your workflow needs.",
    features: [
      "Database polling (MySQL, Postgres, Airtable)",
      "Multi-step data enrichment pipelines",
      "Scheduled reports and daily digests",
      "Webhook processing and routing",
      "Any SaaS-to-SaaS connection",
    ],
    how: "Trigger fires \u2192 Data fetched & transformed \u2192 Actions executed \u2192 Results stored \u2192 Notifications sent",
    tools: ["Make.com", "n8n", "Trigger.dev", "Airtable", "Apify"],
  },
];

export default function ServicesPage() {
  return (
    <div className="flex flex-col">
      {/* Header */}
      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Services
        </h1>
        <p className="mt-4 text-lg text-muted">
          We connect your existing tools into reliable, always-on systems.
          No rip-and-replace. Just automation that works with what you
          already use.
        </p>
      </section>

      {/* Service sections */}
      <div className="mx-auto flex max-w-4xl flex-col gap-16 px-6 pb-20">
        {services.map((service, i) => (
          <section
            key={service.title}
            className="border-t border-border pt-12 first:border-t-0 first:pt-0"
          >
            <div className="mb-1 text-xs font-medium uppercase tracking-widest text-muted">
              0{i + 1}
            </div>
            <h2 className="mb-3 text-xl font-semibold">{service.title}</h2>
            <p className="mb-6 leading-relaxed text-muted">
              {service.description}
            </p>

            <div className="grid gap-8 sm:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wide">
                  What&rsquo;s included
                </h3>
                <ul className="space-y-2">
                  {service.features.map((feature) => (
                    <li
                      key={feature}
                      className="text-sm leading-relaxed text-muted"
                    >
                      <span className="mr-2 text-accent">&bull;</span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wide">
                  How it works
                </h3>
                <p className="mb-6 text-sm leading-relaxed text-muted">
                  {service.how}
                </p>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wide">
                  Tools
                </h3>
                <div className="flex flex-wrap gap-2">
                  {service.tools.map((tool) => (
                    <span
                      key={tool}
                      className="rounded-full border border-border px-3 py-1 text-xs text-muted"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>

      {/* Pricing approach */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <h2 className="mb-3 text-xl font-semibold">Pricing</h2>
          <p className="mb-6 text-muted">
            Every project is scoped individually based on the systems involved,
            the complexity of the workflow, and the level of ongoing support
            needed. We provide a detailed proposal before any work begins.
          </p>
          <Link
            href="/contact"
            className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
          >
            Request a Quote
          </Link>
        </div>
      </section>
    </div>
  );
}
