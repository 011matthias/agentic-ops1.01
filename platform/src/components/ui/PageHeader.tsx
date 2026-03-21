interface PageHeaderProps {
  title: string
  subtitle?: string
  className?: string
  action?: React.ReactNode
}

export default function PageHeader({ title, subtitle, className = "", action }: PageHeaderProps) {
  return (
    <div className={`mb-8 ${className}`}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm text-muted">{subtitle}</p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
    </div>
  )
}
