import type { ReactNode } from "react"
import { auth, signOut } from "@/lib/auth"
import { redirect } from "next/navigation"
import PortalSidebar from "@/components/portal/PortalSidebar"

export default async function PortalLayout({
  children,
}: {
  children: ReactNode
}) {
  const session = await auth()

  if (!session?.user) {
    redirect("/login")
  }

  // Prospects see a pending-approval page instead of the full portal
  if (session.user.role === "prospect") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-gray-950">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="w-14 h-14 mx-auto rounded-full bg-blue-500/10 flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Account Under Review
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">
            Your account has been created and is pending approval. We&apos;ll
            notify you by email once you have access to the client portal.
          </p>
          <form
            action={async () => {
              "use server"
              await signOut({ redirectTo: "/" })
            }}
          >
            <button
              type="submit"
              className="px-5 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Sign out
            </button>
          </form>
        </div>
      </div>
    )
  }

  const user = session.user

  async function handleSignOut() {
    "use server"
    await signOut({ redirectTo: "/" })
  }

  return (
    <div className="min-h-screen flex flex-col sm:flex-row">
      <PortalSidebar
        userName={user.name ?? null}
        userEmail={user.email ?? null}
        userRole={user.role}
        signOutAction={handleSignOut}
      />
      <main className="flex-1 bg-gray-50 dark:bg-gray-950 min-h-screen">
        {children}
      </main>
    </div>
  )
}
