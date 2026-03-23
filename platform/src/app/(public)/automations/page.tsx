import type { Metadata } from "next"
import Link from "next/link"
import { customItems, readyItems } from "@/content/catalog"
import { CatalogCard } from "@/components/catalog/CatalogCard"

export const metadata: Metadata = {
  title: "Automation Services",
  description:
    "Custom-built automations tailored to your workflow, plus ready-to-use templates and systems you can start with today.",
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
            href="#ready-setup"
            className="text-sm font-medium text-accent hover:text-accent-light"
          >
            Ready Setup &rarr;
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

      {/* Section 2: Ready Setup */}
      <section id="ready-setup" className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <div className="mb-10">
            <div className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">
              Ready Setup
            </div>
            <h2 className="mb-3 text-2xl font-semibold tracking-tight">
              Ready when you are
            </h2>
            <p className="max-w-2xl text-muted">
              Self-guided systems and templates you can use immediately. No
              waiting for a build.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {readyItems.map((item) => (
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
            Book a free 20-minute call and we&rsquo;ll tell you exactly what
            would have the most impact.
          </p>
          <Link
            href="/contact"
            className="mt-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
          >
            Book a call
          </Link>
        </div>
      </section>
    </div>
  )
}
