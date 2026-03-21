"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import ThemeToggle from "@/components/ThemeToggle"

const navLinks = [
  { href: "/portal", label: "Dashboard", icon: DashboardIcon, exact: true },
  { href: "/portal/automations", label: "Automations", icon: AutomationsIcon },
  { href: "/portal/messages", label: "Messages", icon: MessagesIcon },
  { href: "/portal/files", label: "Files", icon: FilesIcon },
  { href: "/portal/resources", label: "Resources", icon: ResourcesIcon },
  { href: "/portal/settings", label: "Settings", icon: SettingsIcon },
]

interface PortalSidebarProps {
  userName: string | null
  userEmail: string | null
  userRole: string
  signOutAction: () => Promise<void>
}

export default function PortalSidebar({ userName, userEmail, userRole, signOutAction }: PortalSidebarProps) {
  const pathname = usePathname()

  function isActive(href: string, exact?: boolean) {
    if (exact) return pathname === href
    return pathname === href || pathname.startsWith(href + "/")
  }

  return (
    <aside className="w-full sm:w-60 sm:min-h-screen bg-gray-950 text-gray-100 flex flex-col shrink-0 border-r border-gray-800/50">
      {/* Brand */}
      <div className="px-5 py-4 border-b border-gray-800/50">
        <Link
          href="/portal"
          className="text-sm font-semibold tracking-tight text-white hover:text-gray-200 transition-colors"
        >
          UnpauseAI
        </Link>
        <p className="text-[11px] text-gray-500 mt-0.5 tracking-wide uppercase">Portal</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3">
        <ul className="space-y-0.5">
          {navLinks.map((link) => {
            const active = isActive(link.href, link.exact)
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${
                    active
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                  }`}
                >
                  <link.icon active={active} />
                  {link.label}
                </Link>
              </li>
            )
          })}
        </ul>

        {/* Section divider */}
        <div className="mt-4 pt-4 border-t border-gray-800/50">
          <p className="px-3 mb-2 text-[10px] font-medium text-gray-600 uppercase tracking-wider">Navigate</p>
          {userRole === "admin" && (
            <Link
              href="/admin"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 transition-colors"
            >
              <AdminIcon />
              Admin Panel
            </Link>
          )}
          <Link
            href="/"
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 transition-colors"
          >
            <WebsiteIcon />
            Website
          </Link>
        </div>
      </nav>

      {/* User info + sign out */}
      <div className="px-3 py-3 border-t border-gray-800/50">
        <div className="px-3 py-2">
          <p className="text-[13px] font-medium text-white truncate">{userName ?? "User"}</p>
          <p className="text-[11px] text-gray-500 truncate">{userEmail ?? ""}</p>
        </div>
        <div className="flex items-center gap-1 px-2 mt-1">
          <ThemeToggle className="text-gray-500 hover:text-white hover:bg-gray-800 p-1.5 rounded-md" />
          <form action={signOutAction}>
            <button
              type="submit"
              className="text-[12px] text-gray-500 hover:text-white px-2 py-1.5 rounded-md hover:bg-gray-800 transition-colors"
            >
              Sign out
            </button>
          </form>
        </div>
      </div>
    </aside>
  )
}

/* ── Inline SVG icons (16x16, stroke-based) ── */

function DashboardIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
    </svg>
  )
}

function AutomationsIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1v4M8 11v4M1 8h4M11 8h4" />
      <circle cx="8" cy="8" r="2" />
    </svg>
  )
}

function MessagesIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h12v8H4l-2 2V3z" />
    </svg>
  )
}

function FilesIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" />
      <path d="M9 1v4h4" />
    </svg>
  )
}

function ResourcesIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 2h4v4H2zM10 2h4v4h-4zM2 10h4v4H2z" />
      <path d="M10 12h4M12 10v4" />
    </svg>
  )
}

function SettingsIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" />
    </svg>
  )
}

function AdminIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1l6 3v4c0 3.31-2.69 6-6 7-3.31-1-6-3.69-6-7V4l6-3z" />
    </svg>
  )
}

function WebsiteIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M2 8h12M8 2c2 2 2 10 0 12M8 2c-2 2-2 10 0 12" />
    </svg>
  )
}
