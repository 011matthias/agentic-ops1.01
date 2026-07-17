import Link from "next/link";
import Card from "@/components/ui/Card";
import ScrollReveal from "@/components/ScrollReveal";

/* ─── Data ─── */

const iconStyles = {
  blue: "bg-blue/10 text-blue",
  purple: "bg-purple/10 text-purple",
  green: "bg-green/10 text-green",
  orange: "bg-orange/10 text-orange",
} as const;

const services = [
  {
    title: "Healthcare & Patient Journey Automation",
    description:
      "GDPR-compliant patient workflows, consent tracking, multi-step routing, and full audit trails for regulated environments.",
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
      "Bidirectional sync between your CRM and ERP. Deduplication, automated invoicing, conflict resolution, and status-driven workflows.",
    color: "purple" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    title: "AI-Powered Outreach & Classification",
    description:
      "Claude API integration, confidence-threshold routing, smart follow-up sequences, and AI-driven lead scoring.",
    color: "green" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    title: "Migration & Platform Consolidation",
    description:
      "Make.com and n8n migrations, zero-downtime cutovers, legacy system replacement, and platform consolidation.",
    color: "orange" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
      </svg>
    ),
  },
];

const trustSignals = [
  { label: "3 \u2013 7 weeks", sublabel: "average delivery" },
  { label: "GDPR-compliant", sublabel: "by design" },
  { label: "EU-based", sublabel: "CET timezone" },
];

const processSteps = [
  { step: "01", title: "Discovery", description: "We learn your tools, pain points, and workflow gaps.", color: "blue" as const },
  { step: "02", title: "Proposal", description: "Detailed scope, architecture, and timeline. We discuss commercials on a call.", color: "purple" as const },
  { step: "03", title: "Build & Test", description: "Built with real data, tested every path, iterated until solid.", color: "green" as const },
  { step: "04", title: "Handoff", description: "You own it. Documentation, monitoring, independent operation.", color: "orange" as const },
];

const stepColors = {
  blue: "bg-blue text-white",
  purple: "bg-purple text-white",
  green: "bg-green text-white",
  orange: "bg-orange text-white",
};

const platforms = [
  { name: "Make.com", description: "Visual workflow automation", color: "blue" as const },
  { name: "n8n", description: "Self-hosted data pipelines", color: "purple" as const },
  { name: "Trigger.dev", description: "Code-first AI workflows", color: "green" as const },
  { name: "Claude API", description: "Agentic AI & classification", color: "orange" as const },
];

const platformStyles = {
  blue: "border-blue/20 bg-gradient-to-br from-blue-bg to-transparent text-blue hover:glow-blue",
  purple: "border-purple/20 bg-gradient-to-br from-purple-bg to-transparent text-purple hover:glow-purple",
  green: "border-green/20 bg-gradient-to-br from-green-bg to-transparent text-green hover:glow-green",
  orange: "border-orange/20 bg-gradient-to-br from-orange-bg to-transparent text-orange hover:glow-orange",
};

/* ─── Page ─── */

export default function Home() {
  return (
    <div className="flex flex-col">

      {/* ── Section 1: Hero ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,var(--color-border)_1px,transparent_0)] bg-[length:24px_24px] opacity-40" />
        <div className="relative mx-auto flex max-w-3xl flex-col items-center gap-5 px-6 py-28 text-center sm:py-36">
          <span className="animate-stagger-1 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            EU-Based Automation Consultancy
          </span>
          <h1 className="animate-stagger-2 text-5xl font-extrabold tracking-tight sm:text-6xl">
            Custom automation for businesses that can&rsquo;t afford to get it wrong
          </h1>
          <p className="animate-stagger-3 text-xl font-semibold text-accent">
            Built to stay done.
          </p>
          <p className="animate-stagger-4 max-w-xl text-lg leading-relaxed text-muted">
            Compliant, production-grade workflow automation for regulated
            industries and scaling operations. GDPR-aware. Platform-agnostic.
            Delivered in weeks, not months.
          </p>
          <div className="animate-stagger-5 flex flex-col gap-3 sm:flex-row sm:gap-4">
            <Link
              href="/assessment"
              className="rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Get Your Assessment
            </Link>
            <Link
              href="#process"
              className="rounded-full border border-border px-7 py-3 text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
            >
              See How We Work
            </Link>
          </div>
        </div>
      </section>

      {/* ── Section 2: Trust Signals Strip ── */}
      <ScrollReveal>
        <section className="border-y border-border bg-surface/50">
          <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 px-6 py-10 sm:flex-row sm:justify-between sm:gap-0">
            {trustSignals.map((signal, i) => (
              <div key={signal.label} className="flex flex-col items-center text-center">
                <span className="text-lg font-bold tracking-tight">{signal.label}</span>
                <span className="text-xs text-muted">{signal.sublabel}</span>
                {i < trustSignals.length - 1 && (
                  <div className="mt-6 h-px w-12 bg-border sm:hidden" />
                )}
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 3: What We Build ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
              Capabilities
            </span>
            <h2 className="text-3xl font-bold tracking-tight">
              What we build
            </h2>
            <p className="mt-3 text-muted">
              Production-grade automations for businesses where reliability is non-negotiable.
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
      </ScrollReveal>

      {/* ── Section 4: How We Work ── */}
      <ScrollReveal>
        <section id="process" className="border-y border-border">
          <div className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
            <div className="mb-12 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Process
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                How we work
              </h2>
              <p className="mt-3 text-muted">
                Four phases from first conversation to independent operation.
              </p>
            </div>

            {/* Timeline */}
            <div className="relative grid gap-8 sm:grid-cols-4">
              {/* Connecting line (desktop only) */}
              <div className="absolute left-0 right-0 top-5 hidden h-0.5 bg-gradient-to-r from-blue/30 via-purple/30 to-orange/30 sm:block" />

              {processSteps.map((item) => (
                <div key={item.step} className="relative flex flex-col items-center text-center">
                  <div className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full ${stepColors[item.color]} text-sm font-bold shadow-md`}>
                    {item.step}
                  </div>
                  <h3 className="mt-4 font-semibold">{item.title}</h3>
                  <p className="mt-1 text-sm text-muted">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 5: Platform Expertise ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
          <p className="mb-8 text-center text-xs font-semibold uppercase tracking-wider text-muted">
            We pick the right platform for your workflow
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {platforms.map((platform) => (
              <div
                key={platform.name}
                className={`flex flex-col items-center gap-1 rounded-xl border ${platformStyles[platform.color]} px-4 py-5 text-center transition-all hover:-translate-y-0.5`}
              >
                <span className="text-sm font-bold">{platform.name}</span>
                <span className="text-xs text-muted">{platform.description}</span>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 6: Results ── */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
            <div className="mb-12 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Results
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                What our clients get
              </h2>
            </div>

            <div className="grid gap-6 sm:grid-cols-3">
              <div className="rounded-xl border border-border bg-blue-bg/50 p-6 text-center transition-all hover:-translate-y-0.5">
                <div className="mb-1 text-3xl font-extrabold text-blue">&lt; 60s</div>
                <div className="text-sm font-medium">Response time</div>
                <div className="mt-1 text-xs text-muted">Down from 24-48 hours for lead follow-ups</div>
              </div>
              <div className="rounded-xl border border-border bg-purple-bg/50 p-6 text-center transition-all hover:-translate-y-0.5">
                <div className="mb-1 text-3xl font-extrabold text-purple">Zero</div>
                <div className="text-sm font-medium">Downtime migrations</div>
                <div className="mt-1 text-xs text-muted">Platform cutovers without service interruption</div>
              </div>
              <div className="rounded-xl border border-border bg-green-bg/50 p-6 text-center transition-all hover:-translate-y-0.5">
                <div className="mb-1 text-3xl font-extrabold text-green">30 days</div>
                <div className="text-sm font-medium">Post-launch support</div>
                <div className="mt-1 text-xs text-muted">Included with every implementation</div>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 6b: Testimonials ── */}
      <ScrollReveal>
        <section className="bg-gradient-to-b from-transparent via-surface/50 to-transparent">
          <div className="mx-auto max-w-4xl px-6 py-16">
            <p className="mb-8 text-center text-xs font-semibold uppercase tracking-wider text-muted">
              What clients say
            </p>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="rounded-xl border border-border bg-surface p-6">
                <p className="mb-4 text-sm leading-relaxed text-muted italic">
                  &ldquo;The automation handles everything now. We went from
                  manually responding to every enquiry to having personalized
                  follow-ups running within seconds. Our team focuses on closing
                  instead of chasing.&rdquo;
                </p>
                <div className="text-sm">
                  <span className="font-semibold">Operations Manager</span>
                  <span className="text-muted">, Media &amp; Events Company</span>
                </div>
              </div>
              <div className="rounded-xl border border-border bg-surface p-6">
                <p className="mb-4 text-sm leading-relaxed text-muted italic">
                  &ldquo;We migrated 15 workflows from Zapier without a single
                  hour of downtime. The error handling alone is worth it. We
                  actually know when something breaks now instead of finding out
                  days later.&rdquo;
                </p>
                <div className="text-sm">
                  <span className="font-semibold">Technical Lead</span>
                  <span className="text-muted">, Professional Services Firm</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 6c: Founder ── */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-3xl px-6 py-12 text-center">
            <p className="text-muted">
              Founded by{" "}
              <Link href="/about" className="font-medium text-foreground hover:text-accent transition-colors">
                Nicolas Neumann
              </Link>
              , based in Karlsruhe, Germany. We work with businesses across
              Europe that need automation infrastructure they can trust.
            </p>
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 7: Quick Links ── */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-4xl px-6 py-16">
            <div className="grid gap-4 sm:grid-cols-3">
              <Link
                href="/compare"
                className="group rounded-xl border border-border bg-surface p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <h3 className="mb-1 font-semibold transition-colors group-hover:text-accent">
                  Compare options
                </h3>
                <p className="text-sm text-muted">
                  See how we compare to freelancers, agencies, and building in-house.
                </p>
                <span className="mt-3 inline-block text-sm font-medium text-accent">
                  View comparison &rarr;
                </span>
              </Link>
              <Link
                href="/pricing"
                className="group rounded-xl border border-border bg-surface p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <h3 className="mb-1 font-semibold transition-colors group-hover:text-accent">
                  Transparent pricing
                </h3>
                <p className="text-sm text-muted">
                  Fixed prices for every automation. Self-service from $99, custom from EUR 2,500.
                </p>
                <span className="mt-3 inline-block text-sm font-medium text-accent">
                  View pricing &rarr;
                </span>
              </Link>
              <Link
                href="/blog"
                className="group rounded-xl border border-border bg-surface p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <h3 className="mb-1 font-semibold transition-colors group-hover:text-accent">
                  Learn from our blog
                </h3>
                <p className="text-sm text-muted">
                  Platform comparisons, automation strategy, and lessons from production.
                </p>
                <span className="mt-3 inline-block text-sm font-medium text-accent">
                  Read the blog &rarr;
                </span>
              </Link>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── Section 8: CTA ── */}
      <ScrollReveal>
        <section className="bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
          <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 sm:py-24 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              Tell us what you&rsquo;re automating
            </h2>
            <p className="max-w-lg text-muted">
              Describe your workflow. Within 24 hours, you&rsquo;ll receive a
              written assessment: what we&rsquo;d build, how long it takes, and
              how we&rsquo;d approach it.
            </p>
            <Link
              href="/assessment"
              className="mt-2 rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
            >
              Request Assessment
            </Link>
          </div>
        </section>
      </ScrollReveal>
    </div>
  );
}
