interface PortalCardProps {
  title: string
  description: string
  href: string
  icon: string
  empty?: boolean
  className?: string
}

export default function PortalCard({
  title,
  description,
  href,
  icon,
  empty,
  className = "",
}: PortalCardProps) {
  return (
    <a
      href={href}
      className={`group block rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:border-gray-400 dark:hover:border-gray-600 transition-colors ${className}`}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
          &rarr;
        </span>
      </div>
      <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{title}</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
      {empty && (
        <p className="mt-3 text-xs text-gray-400 dark:text-gray-600 italic">
          Coming soon
        </p>
      )}
    </a>
  )
}
