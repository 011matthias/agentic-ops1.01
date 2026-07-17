import type { Metadata } from "next";
import Link from "next/link";
import { AccordionItem } from "@/components/Accordion";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "FAQ",
  description:
    "Frequently asked questions about UnpauseAI automation services. Process, pricing, platforms, security, and ongoing support.",
};

const sections = [
  {
    title: "Process",
    color: "blue" as const,
    items: [
      {
        q: "How does a project typically start?",
        a: "It starts with your $1 assessment. You describe the workflow you want automated, and within 24 hours you receive a written evaluation: what we'd build, which platform fits, estimated timeline, and cost. If it makes sense for both sides, we move to a formal proposal.",
      },
      {
        q: "How long does a typical project take?",
        a: "Most projects are delivered in 3 to 7 weeks. Simple automations (lead follow-up, database polling) can be done in 1 to 2 weeks. Complex multi-system integrations with custom logic take 4 to 7 weeks. We give you a specific timeline in the proposal.",
      },
      {
        q: "What does the handoff look like?",
        a: "You get the automation running in your own accounts, full documentation, and a walkthrough. We don't keep access after handoff unless you ask us to. The system runs independently without depending on us.",
      },
      {
        q: "Do you work with existing systems or replace them?",
        a: "We connect what you already use. No rip-and-replace. If you're on HubSpot, Fortnox, Gmail, Slack, or anything with an API, we build around it. The goal is automation that fits your stack, not one that forces you to change it.",
      },
    ],
  },
  {
    title: "Pricing & Payment",
    color: "purple" as const,
    items: [
      {
        q: "How much does a project cost?",
        a: "Self-service blueprints range from $99 to $349. Premium implementations (we build it for you) range from $800 to $2,500. Custom projects start at EUR 2,500. Every project is priced upfront with a detailed proposal before work begins.",
      },
      {
        q: "Do you bill hourly?",
        a: "No. All projects are fixed price for a defined scope. If the scope changes during the project, we re-scope and agree on the new price before continuing. No surprise invoices.",
      },
      {
        q: "What payment methods do you accept?",
        a: "Stripe for blueprints and assessments (card payments). Bank transfer (SEPA) for custom projects. We invoice milestone-based for larger projects: typically 50% upfront, 50% on delivery.",
      },
      {
        q: "What if the automation doesn't work as promised?",
        a: "Every project includes 30 days of post-launch support. If something breaks or doesn't behave as scoped, we fix it at no extra cost. We test with real data before handoff specifically to catch edge cases early.",
      },
    ],
  },
  {
    title: "Technical",
    color: "green" as const,
    items: [
      {
        q: "Which platforms do you use?",
        a: "Make.com for visual workflow automation, n8n for self-hosted data pipelines, Trigger.dev for code-first AI workflows, and Claude API for classification and agentic tasks. We pick the platform that fits your requirements, not the one we prefer.",
      },
      {
        q: "Can you integrate with our existing tools?",
        a: "If it has an API, webhook, or database connection, yes. We've integrated with HubSpot, Pipedrive, Fortnox, Upsales, Google Sheets, Gmail, Slack, MySQL, Postgres, Airtable, Smartlead, and many others.",
      },
      {
        q: "Do we need to give you access to our accounts?",
        a: "Temporarily, yes. During the build phase, we need access to the relevant tools to configure and test the automation. After handoff, we revoke our access unless you prefer ongoing support.",
      },
      {
        q: "What happens if an automation fails in production?",
        a: "Every automation we build includes error handling and alerting. If something fails, you get notified immediately with details about what went wrong. During the 30-day support period, we investigate and fix it. After that, most failures are self-diagnosable from the error alerts.",
      },
      {
        q: "Can you work with self-hosted tools?",
        a: "Yes. n8n can be deployed on your own infrastructure, and we can connect to self-hosted databases, APIs, and services. We just need network access during the build phase.",
      },
    ],
  },
  {
    title: "Security & Compliance",
    color: "orange" as const,
    items: [
      {
        q: "Is the automation GDPR-compliant?",
        a: "Yes. We build with GDPR in mind by default: data minimization, consent tracking where needed, audit trails for regulated workflows, and EU-based data processing. We use European hosting and infrastructure where required.",
      },
      {
        q: "How do you handle sensitive data?",
        a: "We never store client data outside the systems you already use. Automations process data in transit but don't create additional copies. API keys and credentials stay in your accounts, not ours.",
      },
      {
        q: "Do you sign NDAs?",
        a: "Yes, we're happy to sign mutual NDAs before any discovery or scoping work. Just ask during the assessment follow-up.",
      },
    ],
  },
  {
    title: "Support & Maintenance",
    color: "blue" as const,
    items: [
      {
        q: "What's included in post-launch support?",
        a: "30 days of bug fixes, configuration tweaks, and guidance for edge cases that appear once the automation runs with real data. This is included in every premium implementation and custom project.",
      },
      {
        q: "What if we need changes after 30 days?",
        a: "We offer maintenance agreements for clients who need ongoing updates. Most automations run independently after handoff, but if your workflow changes, we can scope follow-up work as a new project or on a retainer basis.",
      },
      {
        q: "Can we modify the automation ourselves after handoff?",
        a: "Absolutely. You own the system. Make.com and n8n have visual editors that your team can use to make adjustments. We include documentation specifically so you can maintain it independently.",
      },
    ],
  },
];

const sectionColorStyles = {
  blue: "text-blue",
  purple: "text-purple",
  green: "text-green",
  orange: "text-orange",
};

// Generate FAQ structured data for Google rich snippets
const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: sections.flatMap((section) =>
    section.items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    }))
  ),
};

export default function FAQPage() {
  return (
    <div className="flex flex-col">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            FAQ
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Frequently asked questions
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Everything you need to know about working with us. Can&rsquo;t find
            what you&rsquo;re looking for?{" "}
            <Link href="/contact" className="text-accent hover:text-accent-light">
              Get in touch
            </Link>
            .
          </p>
        </div>
      </section>

      {/* FAQ Sections */}
      <div className="mx-auto max-w-3xl px-6 pb-20">
        {sections.map((section) => (
          <ScrollReveal key={section.title}>
            <div className="mb-12">
              <h2 className={`mb-6 text-lg font-bold ${sectionColorStyles[section.color]}`}>
                {section.title}
              </h2>
              <div className="rounded-xl border border-border bg-surface px-6">
                {section.items.map((item) => (
                  <AccordionItem key={item.q} title={item.q}>
                    {item.a}
                  </AccordionItem>
                ))}
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>

      {/* CTA */}
      <section className="border-t border-border bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Still have questions?
          </h2>
          <p className="max-w-lg text-muted">
            We respond to every inquiry within 24 hours. Ask us anything about
            your specific workflow.
          </p>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/contact"
              className="rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Contact Us
            </Link>
            <Link
              href="/assessment"
              className="rounded-full border border-border px-7 py-3 text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
            >
              $1 Assessment
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
