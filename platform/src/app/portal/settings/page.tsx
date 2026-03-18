import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import PageHeader from "@/components/ui/PageHeader"
import Card from "@/components/ui/Card"
import ThemeSection from "./ThemeSection"

export const metadata = { title: "Settings" }

export default async function SettingsPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const user = session.user

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <PageHeader
        title="Settings"
        subtitle="Manage your account and notification preferences."
      />

      <div className="space-y-6">
        {/* Profile section */}
        <section>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">
            Profile
          </h2>
          <Card className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted mb-1">Name</p>
                <p className="text-sm font-medium text-foreground">
                  {user.name ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted mb-1">Email</p>
                <p className="text-sm font-medium text-foreground">
                  {user.email ?? "—"}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted pt-2 border-t border-border">
              Contact your account manager to update profile details.
            </p>
          </Card>
        </section>

        {/* Appearance section */}
        <section>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">
            Appearance
          </h2>
          <ThemeSection />
        </section>

        {/* Notifications section */}
        <section>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">
            Notifications
          </h2>
          <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-foreground">
                  Email notifications for new messages
                </p>
                <p className="text-xs text-muted mt-0.5">
                  Receive an email when your team sends you a new message.
                </p>
              </div>
              {/* Static toggle — no backend yet */}
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500 select-none"
                  aria-disabled="true"
                >
                  Coming soon
                </span>
              </div>
            </div>
          </Card>
        </section>
      </div>
    </div>
  )
}
