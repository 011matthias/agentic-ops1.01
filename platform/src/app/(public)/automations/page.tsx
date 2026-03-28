import type { Metadata } from "next"
import Link from "next/link"
import { customItems, marketplaceItems } from "@/content/catalog"
import { CatalogCard } from "@/components/catalog/CatalogCard"

export const metadata: Metadata = {
  title: "Automation Services",
  description:
    "Custom-built automations tailored to your workflow, plus battle-tested marketplace blueprints you can deploy today.",
}

export default function AutomationsPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Automation Services
        </h1>
        <p className="mt-4 text-lg text-muted">
          Whether you want it built for you or want to hit the ground running
          yourself, we&rsquo;ve got you covered.
        </p>
        <div className="mt-8 flex justify-center gap-6">
          <a
            href="#custom"
            className="text-sm font-medium text-accent hover:text-accent-light"
          >
            Custom Built &rarr;
          </a>
          <a
            href="#marketplace"
            className="text-sm font-medium text-accent hover:text-accent-light"
          >
            Marketplace &rarr;
          </a>
        </div>
      </section>

      {/* Section 1: Custom Built */}
      <section id="custom" className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <div className="mb-10">
            <div className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">
              Custom Built
            </div>
            <h2 className="mb-3 text-2xl font-semibold tracking-tight">
              Built for your exact workflow
            </h2>
            <p className="max-w-2xl text-muted">
              We scope, build, test, and hand over automations tailored to your
              business. Starting from a short discovery call.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            {customItems.map((item) => (
              <CatalogCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      </section>

      {/* Section 2: Marketplace */}
      <section id="marketplace" className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <div className="mb-10">
            <div className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">
              Marketplace
            </div>
            <h2 className="mb-3 text-2xl font-semibold tracking-tight">
              Battle-tested blueprints
            </h2>
            <p className="max-w-2xl text-muted">
              Automation blueprints from real projects. Self-service or we implement for you.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {marketplaceItems.map((item) => (
              <CatalogCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">
            Not sure which is right for you?
          </h2>
          <p className="text-muted">
            Get a personalized assessment of your automation needs for just $1.
          </p>
          <Link
            href="/assessment"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
          >
            Request Assessment &mdash; $1
          </Link>
        </div>
      </section>
    </div>
  )
}
