interface StatCardProps {
  label: string
  value: string
  className?: string
}

export default function StatCard({ label, value, className = "" }: StatCardProps) {
  return (
    <div className={`rounded-2xl border border-gray-200 dark:border-gray-800 border-l-4 border-l-accent bg-white dark:bg-gray-900 p-6 shadow-sm ${className}`}>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}
