import type { ReactNode } from "react"
import { auth, signOut } from "@/lib/auth"
import { redirect } from "next/navigation"
import Link from "next/link"

const navLinks = [
  { href: "/admin", label: "Dashboard", icon: "⚡" },
  { href: "/admin/clients", label: "Clients", icon: "👥" },
  { href: "/admin/projects", label: "Projects", icon: "🗂️" },
  { href: "/admin/messages", label: "Messages", icon: "💬" },
  { href: "/admin/revenue", label: "Revenue", icon: "💰" },
]

export default async function AdminLayout({
  children,
}: {
  children: ReactNode
}) {
  const session = await auth()

  if (!session?.user) {
    redirect("/login")
  }

  if (session.user.role !== "admin") {
    redirect("/portal")
  }

  const user = session.user

  return (
    <div className="min-h-screen flex flex-col sm:flex-row">
      {/* Sidebar */}
      <aside className="w-full sm:w-64 sm:min-h-screen bg-gray-950 dark:bg-gray-950 text-gray-100 flex flex-col shrink-0">
        {/* Brand */}
        <div className="px-6 py-5 border-b border-gray-800">
          <Link
            href="/admin/clients"
            className="text-base font-semibold tracking-tight text-white hover:text-gray-200 transition-colors"
          >
            UnpauseAI
          </Link>
          <p className="text-xs text-gray-500 mt-0.5">Admin Panel</p>
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
