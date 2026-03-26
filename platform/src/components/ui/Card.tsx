import { HTMLAttributes } from "react"

type AccentColor = "blue" | "purple" | "green" | "orange"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  className?: string
  color?: AccentColor
  variant?: "default" | "callout" | "stat"
}

const colorBorders: Record<AccentColor, string> = {
  blue: "border-l-4 border-l-blue bg-blue-bg",
  purple: "border-l-4 border-l-purple bg-purple-bg",
  green: "border-l-4 border-l-green bg-green-bg",
  orange: "border-l-4 border-l-orange bg-orange-bg",
}

const colorAccents: Record<AccentColor, string> = {
  blue: "border-blue/20 bg-blue-bg",
  purple: "border-purple/20 bg-purple-bg",
  green: "border-green/20 bg-green-bg",
  orange: "border-orange/20 bg-orange-bg",
}

export default function Card({ className = "", children, color, variant = "default", ...props }: CardProps) {
  const base = "rounded-xl p-5 transition-all duration-200"

  const variantStyles = {
    default: `border border-border bg-surface shadow-sm hover:shadow-md hover:-translate-y-0.5 ${color ? colorAccents[color] : ""}`,
    callout: `border border-border ${color ? colorBorders[color] : "border-l-4 border-l-accent bg-blue-bg"}`,
    stat: `border border-border bg-surface text-center ${color ? colorAccents[color] : ""}`,
  }

  return (
    <div
      className={`${base} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
