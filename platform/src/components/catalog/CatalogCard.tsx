import Link from "next/link"
import { CatalogItem } from "@/content/catalog"

interface Props {
  item: CatalogItem
}

export function CatalogCard({ item }: Props) {
  const ctaHref =
    item.type === "custom"
      ? `/contact?service=${item.slug}`
      : `/contact?package=${item.slug}`
  const ctaText = item.type === "custom" ? "Get a quote" : "Request access"

  return (
    <div className="relative flex flex-col rounded-lg border border-border bg-background p-6 transition-shadow hover:shadow-sm">
      {/* Popular badge */}
      {item.popular && (
        <span className="absolute right-4 top-4 rounded-full bg-accent px-3 py-0.5 text-xs font-medium text-white">
          Popular
        </span>
      )}

      {/* Header */}
      <div className="mb-3 pr-16">
        <h3 className="text-base font-semibold leading-snug">{item.name}</h3>
        <p className="mt-1 text-sm text-muted">{item.tagline}</p>
      </div>

      {/* Description */}
      <p className="mb-5 text-sm leading-relaxed text-muted">
        {item.description}
      </p>

      {/* What you get */}
      <div className="mb-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide">
          What you get
        </p>
        <ul className="space-y-1.5">
          {item.whatYouGet.map((line) => (
            <li key={line} className="flex items-start gap-2 text-sm text-muted">
              <span className="mt-0.5 shrink-0 text-accent">&#10003;</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Spacer pushes footer to bottom */}
      <div className="flex-1" />

      {/* Tags */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        {item.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-muted">{item.typicalTimeline}</span>
          <span className="text-sm font-semibold">
            {item.startingFrom === "Free" ? "Free" : `From ${item.startingFrom}`}
          </span>
        </div>
        <Link
          href={ctaHref}
          className="shrink-0 rounded-full bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-light"
        >
          {ctaText}
        </Link>
      </div>
    </div>
  )
}
