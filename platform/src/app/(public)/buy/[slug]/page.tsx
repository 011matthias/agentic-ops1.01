import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { catalog } from "@/content/catalog"
import { CheckoutButton } from "@/components/catalog/CheckoutButton"

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const item = catalog.find((i) => i.slug === slug)
  if (!item) return {}
  return {
    title: `Buy ${item.name}`,
    description: item.tagline,
  }
}

export default async function BuyPage({ params }: Props) {
  const { slug } = await params
  const item = catalog.find((i) => i.slug === slug)

  if (!item || item.tier !== "marketplace") {
    notFound()
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      {/* Breadcrumb */}
      <div className="mb-8 text-sm text-muted">
        <Link href="/work" className="hover:text-foreground">
          Marketplace
        </Link>
        <span className="mx-2">/</span>
        <span>{item.name}</span>
      </div>

      {/* Header */}
      <div className="mb-8">
        <div className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">
          {item.category}
        </div>
        <h1 className="mb-2 text-3xl font-bold tracking-tight">{item.name}</h1>
        <p className="text-lg text-muted">{item.tagline}</p>
      </div>

      {/* Description */}
      <p className="mb-8 leading-relaxed text-muted">{item.description}</p>

      {/* Self-service tier */}
      <div className="mb-6 rounded-lg border border-border p-6">
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide">
          Self-Service &mdash; What&rsquo;s included
        </h2>
        <ul className="space-y-3">
          {item.whatYouGet.map((benefit) => (
            <li key={benefit} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 text-accent font-bold">&#10003;</span>
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 flex items-baseline gap-2 border-t border-border pt-4">
          <span className="text-3xl font-bold">{item.selfServicePrice}</span>
          <span className="text-sm text-muted">one-time</span>
        </div>
        <div className="mt-4">
          <CheckoutButton slug={item.slug} />
        </div>
      </div>

      {/* Premium tier */}
      <div className="mb-8 rounded-lg border-2 border-accent/20 bg-gradient-to-br from-blue-bg/50 to-transparent p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-accent">
          Premium &mdash; We implement it for you
        </h2>
        <ul className="space-y-3">
          {item.premiumIncludes.map((benefit) => (
            <li key={benefit} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 text-accent font-bold">&#10003;</span>
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 flex items-baseline gap-2 border-t border-border pt-4">
          <span className="text-3xl font-bold text-accent">{item.premiumPrice}</span>
          <span className="text-sm text-muted">full implementation</span>
        </div>
        <Link
          href={`/contact?package=${item.slug}&tier=premium`}
          className="mt-4 inline-block rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5"
        >
          Request Premium Implementation
        </Link>
      </div>

      {/* Tools */}
      <div className="mb-8">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">
          Built with
        </h2>
        <div className="flex flex-wrap gap-2">
          {item.tools.map((tool) => (
            <span
              key={tool}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted"
            >
              {tool}
            </span>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted">
        Secure checkout via Stripe. You&rsquo;ll receive setup instructions by email after purchase.
      </p>
    </div>
  )
}
