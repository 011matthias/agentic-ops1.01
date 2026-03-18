"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

interface Tab {
  key: string
  label: string
  count?: number
}

interface TabNavProps {
  tabs: Tab[]
  activeTab: string
}

export default function TabNav({ tabs, activeTab }: TabNavProps) {
  const pathname = usePathname()

  return (
    <div className="flex gap-0 border-b border-border mb-8 -mx-4 px-4 overflow-x-auto">
      {tabs.map((tab) => {
        const isActive = tab.key === activeTab
        return (
          <Link
            key={tab.key}
            href={`${pathname}?tab=${tab.key}`}
            className={`px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap -mb-px ${
              isActive
                ? "border-b-2 border-accent text-foreground"
                : "border-b-2 border-transparent text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
            {tab.count != null && (
              <span className={`ml-1.5 ${isActive ? "text-muted" : "text-muted/70"}`}>
                ({tab.count})
              </span>
            )}
          </Link>
        )
      })}
    </div>
  )
}
