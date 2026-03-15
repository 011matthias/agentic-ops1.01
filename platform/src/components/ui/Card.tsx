import { HTMLAttributes } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  className?: string
}

export default function Card({ className = "", children, ...props }: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-border bg-white dark:bg-gray-900 p-6 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
