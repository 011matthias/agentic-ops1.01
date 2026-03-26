import Link from "next/link";

const textSizes = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-xl",
} as const;

interface LogoProps {
  size?: keyof typeof textSizes;
  href?: string;
  className?: string;
}

export default function Logo({ size = "md", href = "/", className = "" }: LogoProps) {
  const content = (
    <span className={`inline-flex items-center ${textSizes[size]} tracking-tight ${className}`}>
      <span className="font-bold">Unpause</span>
      <span className="font-bold text-accent">AI</span>
    </span>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
