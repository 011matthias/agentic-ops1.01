import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Services",
  description:
    "Automation services: lead follow-up, CRM/ERP integration, sales campaign operations, and custom workflow automation.",
};

const colors = ["blue", "purple", "green", "orange"] as const;

const colorStyles = {
  blue: { border: "border-l-blue", bg: "bg-blue-bg", text: "text-blue", badge: "bg-blue/10 text-blue" },
  purple: { border: "border-l-purple", bg: "bg-purple-bg", text: "text-purple", badge: "bg-purple/10 text-purple" },
  green: { border: "border-l-green", bg: "bg-green-bg", text: "text-green", badge: "bg-green/10 text-green" },
  orange: { border: "border-l-orange", bg: "bg-orange-bg", text: "text-orange", badge: "bg-orange/10 text-orange" },
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
    howSteps: ["Form submitted", "Lead scored & logged", "Personalized response sent", "Follow-up sequence activated", "Reply detected", "Team notified"],
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
    howSteps: ["Deal stage changes", "Data synced to ERP", "Invoice generated", "Team notified", "Records updated"],
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
    howSteps: ["Campaign data pulled", "Aggregated in sheets", "Dashboard updated", "Trends calculated", "Reports delivered"],
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
    howSteps: ["Trigger fires", "Data fetched & transformed", "Actions executed", "Results stored", "Notifications sent"],
    tools: ["Make.com", "n8n", "Trigger.dev", "Airtable", "Apify"],
  },
];

export default function ServicesPage() {
  return (
    <div className="flex flex-col">
      {/* Header */}
      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
          What We Do
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
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
        {services.map((service, i) => {
          const color = colors[i];
          const styles = colorStyles[color];
          return (
            <section
              key={service.title}
              className={`rounded-xl border border-border ${styles.border} border-l-4 p-8 transition-all`}
            >
              <div className="mb-2">
                <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${styles.badge}`}>
                  0{i + 1}
                </span>
              </div>
              <h2 className="mb-3 text-xl font-bold">{service.title}</h2>
              <p className="mb-6 leading-relaxed text-muted">
                {service.description}
              </p>

              <div className="grid gap-8 sm:grid-cols-2">
                <div>
                  <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide">
                    What&rsquo;s included
                  </h3>
                  <ul className="space-y-2">
                    {service.features.map((feature) => (
                      <li
                        key={feature}
                        className="text-sm leading-relaxed text-muted"
                      >
                        <span className={`mr-2 ${styles.text}`}>&bull;</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide">
                    How it works
                  </h3>
                  <div className="mb-6 flex flex-wrap items-center gap-1">
                    {service.howSteps.map((step, j) => (
                      <span key={step} className="flex items-center gap-1">
                        <span className={`inline-flex items-center rounded-lg ${styles.bg} px-2.5 py-1 text-xs font-medium ${styles.text}`}>
                          {step}
                        </span>
                        {j < service.howSteps.length - 1 && (
                          <span className="text-xs text-muted">&rarr;</span>
                        )}
                      </span>
                    ))}
                  </div>
                  <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide">
                    Tools
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {service.tools.map((tool) => (
                      <span
                        key={tool}
                        className={`rounded-full px-3 py-1 text-xs font-medium ${styles.badge}`}
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {/* Pricing approach */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <h2 className="mb-3 text-xl font-bold">Pricing</h2>
          <p className="mb-6 text-muted">
            Every project is scoped individually based on the systems involved,
            the complexity of the workflow, and the level of ongoing support
            needed. We provide a detailed proposal before any work begins.
          </p>
          <Link
            href="/contact"
            className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request a Quote
          </Link>
        </div>
      </section>
    </div>
  );
}
