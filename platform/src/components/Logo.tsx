import Link from "next/link";

const textSizes = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-2xl",
} as const;

interface LogoProps {
  size?: keyof typeof textSizes;
  href?: string;
  className?: string;
  showTagline?: boolean;
}

export default function Logo({ size = "md", href = "/", className = "" , showTagline = false}: LogoProps) {
  const content = (
    <span className={`inline-flex items-center gap-2 ${textSizes[size]} tracking-tight ${className}`}>
      {/* Play-button mark */}
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        className="h-[1em] w-[1em] text-accent flex-shrink-0"
      >
        <path d="M8 5.14v13.72a1 1 0 001.5.86l11.04-6.86a1 1 0 000-1.72L9.5 4.28a1 1 0 00-1.5.86z" />
      </svg>
      <span className="font-bold">Unpause</span>
      <span className="-ml-2 font-extrabold text-accent">AI</span>
      {showTagline && (
        <span className="ml-2 hidden text-xs font-normal tracking-normal text-muted sm:inline">
          Built to stay done.
        </span>
      )}
    </span>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
