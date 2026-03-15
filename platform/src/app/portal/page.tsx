import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"

export default async function PortalPage() {
  const session = await auth()

  if (!session?.user) {
    redirect("/login")
  }

  const firstName = session.user.name?.split(" ")[0] ?? "there"

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold">Welcome back, {firstName}</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Here&apos;s an overview of your automations and activity.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
        <StatCard label="Active Automations" value="—" />
        <StatCard label="Runs This Month" value="—" />
        <StatCard label="Open Messages" value="—" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PortalCard
          title="Automations"
          description="View and monitor your active automations, run history, and status."
          href="/portal/automations"
          icon="⚡"
          empty
        />
        <PortalCard
          title="Messages"
          description="Communicate with the UnpauseAI team about your project."
          href="/portal/messages"
          icon="💬"
          empty
        />
        <PortalCard
          title="Reports"
          description="Usage summaries, performance metrics, and monthly digests."
          href="/portal/reports"
          icon="📊"
          empty
        />
        <PortalCard
          title="Settings"
          description="Manage your account, notification preferences, and integrations."
          href="/portal/settings"
          icon="⚙️"
          empty
        />
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function PortalCard({
  title,
  description,
  href,
  icon,
  empty,
}: {
  title: string
  description: string
  href: string
  icon: string
  empty?: boolean
}) {
  return (
    <a
      href={href}
      className="group block rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:border-gray-400 dark:hover:border-gray-600 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
          →
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
