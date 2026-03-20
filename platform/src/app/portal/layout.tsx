import type { ReactNode } from "react"
import { auth, signOut } from "@/lib/auth"
import { redirect } from "next/navigation"
import Link from "next/link"
import ThemeToggle from "@/components/ThemeToggle"

const navLinks = [
  { href: "/portal", label: "Dashboard", icon: "▦" },
  { href: "/portal/automations", label: "Automations", icon: "⚡" },
  { href: "/portal/messages", label: "Messages", icon: "💬" },
  { href: "/portal/files", label: "Files", icon: "📁" },
  { href: "/portal/reports", label: "Reports", icon: "📊" },
  { href: "/portal/resources", label: "Resources", icon: "📚" },
  { href: "/portal/settings", label: "Settings", icon: "⚙️" },
]

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
      <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 mx-auto rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <span className="text-2xl">&#9203;</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Account Under Review
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
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
              className="px-6 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-700 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Sign out
            </button>
          </form>
        </div>
      </div>
    )
  }

  // After checks, session and user are guaranteed to be a client or admin
  const user = session!.user

  return (
    <div className="min-h-screen flex flex-col sm:flex-row">
      {/* Sidebar */}
      <aside className="w-full sm:w-64 sm:min-h-screen bg-gray-950 dark:bg-gray-950 text-gray-100 flex flex-col shrink-0">
        {/* Brand */}
        <div className="px-6 py-5 border-b border-gray-800">
          <Link
            href="/portal"
            className="text-base font-semibold tracking-tight text-white hover:text-gray-200 transition-colors"
          >
            UnpauseAI
          </Link>
          <p className="text-xs text-gray-500 mt-0.5">Client Portal</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-4 py-4">
          <ul className="space-y-1">
            {navLinks.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800 transition-colors"
                >
                  <span className="text-base leading-none">{link.icon}</span>
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* User info + sign out */}
        <div className="px-4 py-4 border-t border-gray-800">
          <div className="px-3 py-2 mb-1">
            <p className="text-sm font-medium text-white truncate">{user.name ?? "—"}</p>
            <p className="text-xs text-gray-500 truncate">{user.email ?? "—"}</p>
          </div>
          <div className="flex items-center gap-2 px-1 mb-2">
            <ThemeToggle className="text-gray-400 hover:text-white hover:bg-gray-800" />
          </div>
          <form
            action={async () => {
              "use server"
              await signOut({ redirectTo: "/" })
            }}
          >
            <button
              type="submit"
              className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50 dark:bg-gray-900 min-h-screen">
        {children}
      </main>
    </div>
  )
}
