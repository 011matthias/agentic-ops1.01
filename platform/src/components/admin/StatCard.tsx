interface StatCardProps {
  label: string
  value: string | number
  sublabel?: string
}

export default function StatCard({ label, value, sublabel }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-sm">
      <p className="text-xs font-medium text-muted uppercase tracking-wider">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground tabular-nums">{value}</p>
      {sublabel && (
        <p className="mt-1 text-xs text-muted">{sublabel}</p>
      )}
    </div>
  )
}
