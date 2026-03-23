"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import ThemeToggle from "@/components/ThemeToggle"
import Logo from "@/components/Logo"

const navLinks = [
  { href: "/admin", label: "Dashboard", icon: DashboardIcon, exact: true },
  { href: "/admin/clients", label: "Clients", icon: ClientsIcon },
  { href: "/admin/projects", label: "Projects", icon: ProjectsIcon },
  { href: "/admin/builds", label: "Builds", icon: BuildsIcon },
  { href: "/admin/messages", label: "Messages", icon: MessagesIcon },
  { href: "/admin/architecture", label: "Architecture", icon: ArchIcon },
]

interface AdminSidebarProps {
  userName: string | null
  userEmail: string | null
  signOutAction: () => Promise<void>
}

export default function AdminSidebar({ userName, userEmail, signOutAction }: AdminSidebarProps) {
  const pathname = usePathname()

  function isActive(href: string, exact?: boolean) {
    if (exact) return pathname === href
    return pathname === href || pathname.startsWith(href + "/")
  }

  return (
    <aside className="w-full sm:w-60 sm:min-h-screen bg-gray-950 text-gray-100 flex flex-col shrink-0 border-r border-gray-800/50">
      {/* Blue accent bar — distinguishes admin from portal */}
      <div className="h-1 bg-blue-500" />
      {/* Brand */}
      <div className="px-5 py-4 border-b border-gray-800/50">
        <Logo size="sm" href="/admin" className="text-white hover:text-gray-200 transition-colors" />
        <p className="text-xs text-blue-400 mt-0.5 font-semibold tracking-wide uppercase">Admin</p>
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
          <p className="px-3 mb-2 text-[10px] font-medium text-gray-600 uppercase tracking-wider">Switch</p>
          <Link
            href="/portal"
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 transition-colors"
          >
            <PortalIcon />
            Client Portal
          </Link>
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
          <p className="text-[13px] font-medium text-white truncate">{userName ?? "Admin"}</p>
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

function ClientsIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="5" r="2.5" />
      <path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" />
    </svg>
  )
}

function ProjectsIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4.5h12M2 8h12M2 11.5h8" />
    </svg>
  )
}

function BuildsIcon({ active }: { active?: boolean }) {
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

function ArchIcon({ active }: { active?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={active ? "#fff" : "currentColor"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="1.5" width="6" height="4" rx="1" />
      <rect x="1" y="10.5" width="5" height="4" rx="1" />
      <rect x="10" y="10.5" width="5" height="4" rx="1" />
      <path d="M8 5.5v2.5M8 8H3.5v2.5M8 8h4.5v2.5" />
    </svg>
  )
}

function PortalIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="12" height="12" rx="2" />
      <path d="M2 6h12" />
      <path d="M6 6v8" />
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
