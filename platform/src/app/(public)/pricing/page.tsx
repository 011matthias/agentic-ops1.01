import type { Metadata } from "next";
import Link from "next/link";
import { marketplaceItems, customItems } from "@/content/catalog";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Transparent pricing for automation services. Self-service blueprints from $99, full implementations from $800, custom projects from EUR 2,500.",
};

const faqs = [
  {
    q: "How does pricing work for custom projects?",
    a: "Every custom project starts with a scoped proposal. We assess the systems involved, the workflow complexity, and the level of testing required, then provide a fixed price before any work begins. No hourly surprises.",
  },
  {
    q: "What's the difference between self-service and premium?",
    a: "Self-service gives you the blueprint file and documentation to set it up yourself. Premium means we implement it in your accounts, configure it with your data, test every path, and provide 30 days of post-launch support.",
  },
  {
    q: "Do you charge hourly or fixed?",
    a: "Fixed price for defined scopes. We scope the project upfront so you know exactly what you're paying before we start. If the scope changes, we re-scope and agree on the new price first.",
  },
  {
    q: "What's included in 30-day post-launch support?",
    a: "Bug fixes, configuration adjustments, and guidance for edge cases that appear once the automation runs with real production data. Not a retainer, just making sure what we built stays running.",
  },
  {
    q: "Can I start with a blueprint and upgrade to premium later?",
    a: "Yes. If you buy a self-service blueprint and decide you want us to implement it, the blueprint price is credited toward the premium implementation.",
  },
  {
    q: "What if I need ongoing changes after the 30 days?",
    a: "We offer maintenance agreements for clients who need regular updates. Most automations run independently after handoff, but if your workflow evolves, we can scope follow-up work as a new project.",
  },
];

export default function PricingPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            Pricing
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Transparent pricing, fixed scope
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Every project is scoped and priced before work begins. No hourly
            billing, no surprises. Pick a ready-made blueprint or let us build
            something custom.
          </p>
        </div>
      </section>

      {/* Tier Overview */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20">
          <div className="grid gap-6 md:grid-cols-3">
            {/* Self-Service Tier */}
            <div className="flex flex-col rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-lg">
              <span className="mb-4 inline-block self-start rounded-full bg-green-bg px-3 py-1 text-xs font-semibold text-green">
                Self-Service
              </span>
              <div className="mb-2 text-3xl font-extrabold">$99 &ndash; $349</div>
              <p className="mb-6 text-sm text-muted">
                Blueprint file + documentation. You set it up in your own accounts.
              </p>
              <ul className="mb-8 space-y-3 text-sm text-muted">
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Make.com or n8n workflow file
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Step-by-step setup documentation
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Video walkthrough included
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Upgradable to premium (price credited)
                </li>
              </ul>
              <Link
                href="/work"
                className="mt-auto rounded-full border border-border px-6 py-2.5 text-center text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
              >
                Browse Blueprints
              </Link>
            </div>

            {/* Premium Tier */}
            <div className="relative flex flex-col rounded-xl border-2 border-accent bg-surface p-6 shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-xl">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-4 py-1 text-xs font-semibold text-white">
                Most Popular
              </span>
              <span className="mb-4 inline-block self-start rounded-full bg-blue-bg px-3 py-1 text-xs font-semibold text-blue">
                Premium
              </span>
              <div className="mb-2 text-3xl font-extrabold">$800 &ndash; $2,500</div>
              <p className="mb-6 text-sm text-muted">
                We implement the automation in your accounts, test it, and support it for 30 days.
              </p>
              <ul className="mb-8 space-y-3 text-sm text-muted">
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Full implementation in your accounts
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Custom configuration for your data
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Tested with real production data
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  30-day post-launch support
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Documentation and handoff
                </li>
              </ul>
              <Link
                href="/work"
                className="mt-auto rounded-full bg-accent px-6 py-2.5 text-center text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
              >
                View Automations
              </Link>
            </div>

            {/* Custom Tier */}
            <div className="flex flex-col rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-lg">
              <span className="mb-4 inline-block self-start rounded-full bg-orange-bg px-3 py-1 text-xs font-semibold text-orange">
                Custom
              </span>
              <div className="mb-2 text-3xl font-extrabold">From EUR 2,500</div>
              <p className="mb-6 text-sm text-muted">
                Fully scoped project. Discovery, proposal, implementation, testing, and documentation.
              </p>
              <ul className="mb-8 space-y-3 text-sm text-muted">
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Discovery call to map your workflow
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Written proposal with architecture
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Full build, test, and handoff
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Team training and documentation
                </li>
                <li className="flex items-start gap-2">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-orange" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  30-day post-launch support
                </li>
              </ul>
              <Link
                href="/assessment"
                className="mt-auto rounded-full border border-border px-6 py-2.5 text-center text-sm font-medium transition-all hover:bg-surface-hover hover:-translate-y-0.5"
              >
                Get Your $1 Assessment
              </Link>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Product Breakdown */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="mb-12 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Detailed Pricing
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                Automation catalog
              </h2>
              <p className="mt-3 text-muted">
                Each automation with self-service and premium pricing side by side.
              </p>
            </div>

            {/* Table */}
            <div className="overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface">
                    <th className="px-6 py-4 text-left font-semibold">Automation</th>
                    <th className="px-6 py-4 text-left font-semibold">Category</th>
                    <th className="px-6 py-4 text-right font-semibold">Self-Service</th>
                    <th className="px-6 py-4 text-right font-semibold">Premium</th>
                  </tr>
                </thead>
                <tbody>
                  {marketplaceItems.map((item) => (
                    <tr key={item.id} className="border-b border-border transition-colors hover:bg-surface-hover">
                      <td className="px-6 py-4">
                        <div className="font-medium">{item.name}</div>
                        <div className="mt-0.5 text-xs text-muted">{item.tagline}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="rounded-full bg-blue-bg px-2.5 py-0.5 text-xs font-medium text-blue">
                          {item.category}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-medium">{item.selfServicePrice}</td>
                      <td className="px-6 py-4 text-right font-bold text-accent">{item.premiumPrice}</td>
                    </tr>
                  ))}
                  {customItems.map((item) => (
                    <tr key={item.id} className="border-b border-border bg-orange-bg/30 transition-colors hover:bg-surface-hover">
                      <td className="px-6 py-4">
                        <div className="font-medium">{item.name}</div>
                        <div className="mt-0.5 text-xs text-muted">{item.tagline}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="rounded-full bg-orange-bg px-2.5 py-0.5 text-xs font-medium text-orange">
                          {item.category}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right text-muted">&mdash;</td>
                      <td className="px-6 py-4 text-right font-bold text-accent">{item.premiumPrice}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* FAQ */}
      <ScrollReveal>
        <section className="border-t border-border">
          <div className="mx-auto max-w-3xl px-6 py-20">
            <div className="mb-12 text-center">
              <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-wider text-muted">
                Questions
              </span>
              <h2 className="text-3xl font-bold tracking-tight">
                Pricing FAQ
              </h2>
            </div>

            <div className="space-y-6">
              {faqs.map((faq) => (
                <div key={faq.q} className="rounded-xl border border-border bg-surface p-6">
                  <h3 className="mb-2 font-semibold">{faq.q}</h3>
                  <p className="text-sm leading-relaxed text-muted">{faq.a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* CTA */}
      <section className="bg-gradient-to-b from-transparent via-accent/[0.03] to-transparent">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Not sure which tier fits?
          </h2>
          <p className="max-w-lg text-muted">
            Describe your workflow and we&rsquo;ll tell you what it would take.
            24-hour turnaround. $1 to filter serious inquiries.
          </p>
          <Link
            href="/assessment"
            className="mt-2 rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request Assessment &mdash; $1
          </Link>
        </div>
      </section>
    </div>
  );
}
