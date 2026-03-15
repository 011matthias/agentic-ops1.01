interface EmptyStateProps {
  title: string
  description: string
  action?: {
    label: string
    href: string
  }
  className?: string
}

export default function EmptyState({
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12 ${className}`}
    >
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted max-w-sm">{description}</p>
      {action && (
        <a
          href={action.href}
          className="mt-6 inline-flex items-center px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          {action.label}
        </a>
      )}
    </div>
  )
}
