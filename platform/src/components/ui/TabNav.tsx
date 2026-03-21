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
            className={`px-3 py-2.5 text-[13px] font-medium transition-colors whitespace-nowrap -mb-px ${
              isActive
                ? "border-b-2 border-foreground text-foreground"
                : "border-b-2 border-transparent text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
            {tab.count != null && (
              <span className={`ml-1.5 text-[11px] px-1.5 py-0.5 rounded-full ${
                isActive
                  ? "bg-foreground/10 text-foreground"
                  : "bg-muted/10 text-muted"
              }`}>
                {tab.count}
              </span>
            )}
          </Link>
        )
      })}
    </div>
  )
}
