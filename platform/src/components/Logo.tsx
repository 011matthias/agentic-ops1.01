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
    <span className={`${sizes[size]} tracking-tight ${className}`}>
      <span className="font-bold">Unpause</span>
      <span className="font-bold text-accent">AI</span>
    </span>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
