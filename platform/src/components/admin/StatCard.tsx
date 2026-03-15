interface StatCardProps {
  label: string
  value: string | number
  sublabel?: string
}

export default function StatCard({ label, value, sublabel }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
      {sublabel && (
        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{sublabel}</p>
      )}
    </div>
  )
}
