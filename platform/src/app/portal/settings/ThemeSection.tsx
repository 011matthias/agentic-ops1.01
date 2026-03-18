"use client"

import { useTheme } from "@/components/ThemeProvider"
import Card from "@/components/ui/Card"

const options = [
  { value: "light" as const, label: "Light" },
  { value: "dark" as const, label: "Dark" },
  { value: "system" as const, label: "System" },
]

export default function ThemeSection() {
  const { theme, setTheme } = useTheme()

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-medium text-foreground">Appearance</p>
        <p className="text-xs text-muted mt-0.5">
          Choose how the portal looks for you.
        </p>
      </div>
      <div className="flex gap-1 rounded-xl bg-gray-100 dark:bg-gray-800 p-1 w-fit">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setTheme(opt.value)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              theme === opt.value
                ? "bg-white dark:bg-gray-700 text-foreground shadow-sm"
                : "text-muted hover:text-foreground"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </Card>
  )
}
