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

  if (!item || item.type !== "ready-setup") {
    notFound()
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      {/* Breadcrumb */}
      <div className="mb-8 text-sm text-muted">
        <Link href="/automations" className="hover:text-foreground">
          Automations
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

      {/* What you get */}
      <div className="mb-8 rounded-lg border border-border p-6">
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide">
          What&rsquo;s included
        </h2>
        <ul className="space-y-3">
          {item.whatYouGet.map((benefit) => (
            <li key={benefit} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 text-accent font-bold">&#10003;</span>
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
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

      {/* Price + CTA */}
      <div className="rounded-lg border border-border p-6">
        <div className="mb-4 flex items-baseline gap-2">
          <span className="text-3xl font-bold">{item.startingFrom}</span>
          <span className="text-sm text-muted">one-time</span>
        </div>
        <CheckoutButton slug={item.slug} />
        <p className="mt-3 text-xs text-muted">
          Secure checkout via Stripe. You&rsquo;ll receive setup instructions by email after purchase.
        </p>
      </div>
    </div>
  )
}
