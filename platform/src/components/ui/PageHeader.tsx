interface PageHeaderProps {
  title: string
  subtitle?: string
  className?: string
}

export default function PageHeader({ title, subtitle, className = "" }: PageHeaderProps) {
  return (
    <div className={`mb-8 ${className}`}>
      <h1 className="text-3xl font-bold text-foreground">{title}</h1>
      {subtitle && (
        <p className="mt-2 text-muted">{subtitle}</p>
      )}
    </div>
  )
}
