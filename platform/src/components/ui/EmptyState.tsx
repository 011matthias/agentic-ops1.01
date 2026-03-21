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
      className={`flex flex-col items-center justify-center text-center rounded-xl border border-dashed border-border p-16 ${className}`}
    >
      <div className="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center mb-4">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M12 8v8M8 12h8" />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted max-w-xs">{description}</p>
      {action && (
        <a
          href={action.href}
          className="mt-5 inline-flex items-center px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          {action.label}
        </a>
      )}
    </div>
  )
}
