import Link from "next/link";

const sizes = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-xl",
} as const;

interface LogoProps {
  size?: keyof typeof sizes;
  href?: string;
  className?: string;
}

export default function Logo({ size = "md", href = "/", className = "" }: LogoProps) {
  const content = (
    <span className={`${sizes[size]} font-semibold tracking-tight ${className}`}>
      <span className="text-accent">Un</span>
      <span>pause</span>
      <span className="text-accent">AI</span>
    </span>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
