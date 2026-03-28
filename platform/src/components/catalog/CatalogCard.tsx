import Link from "next/link"
import type { CatalogItem } from "@/content/catalog"

interface CatalogCardProps {
  item: CatalogItem
}

export function CatalogCard({ item }: CatalogCardProps) {
  const isMarketplace = item.tier === "marketplace"

  return (
    <div className="flex flex-col rounded-lg border border-border p-6">
      <div className="mb-1 text-xs font-medium uppercase tracking-widest text-muted">
        {item.category}
      </div>
      <h3 className="mb-1 text-lg font-semibold">{item.name}</h3>
      <p className="mb-4 text-sm leading-relaxed text-muted">{item.tagline}</p>

      <ul className="mb-6 flex-1 space-y-1.5">
        {item.whatYouGet.map((benefit) => (
          <li key={benefit} className="flex items-start gap-2 text-sm text-muted">
            <span className="mt-0.5 text-accent">&#10003;</span>
            {benefit}
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap gap-1.5 mb-6">
        {item.tools.map((tool) => (
          <span
            key={tool}
            className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted"
          >
            {tool}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
        <div className="text-sm">
          {isMarketplace ? (
            <span className="font-medium">From {item.selfServicePrice}</span>
          ) : (
            <span className="font-medium text-accent">{item.premiumPrice}</span>
          )}
        </div>

        <Link
          href={isMarketplace ? `/buy/${item.slug}` : `/contact?package=${item.slug}`}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          {isMarketplace ? "View details" : "Get in touch"} &rarr;
        </Link>
      </div>
    </div>
  )
}
