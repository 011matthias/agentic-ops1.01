import Link from "next/link";

const iconSizes = {
  sm: 20,
  md: 24,
  lg: 28,
} as const;

const textSizes = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-xl",
} as const;

interface LogoProps {
  size?: keyof typeof textSizes;
  href?: string;
  className?: string;
  iconOnly?: boolean;
}

function LogoIcon({ size }: { size: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      width={size}
      height={size}
      className="flex-shrink-0"
    >
      <rect width="32" height="32" rx="7" fill="#2563eb" />
      <rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white" />
      <polygon points="18,8 23,16 18,24" fill="white" />
    </svg>
  );
}

export default function Logo({ size = "md", href = "/", className = "", iconOnly = false }: LogoProps) {
  const content = (
    <span className={`inline-flex items-center gap-1.5 ${textSizes[size]} tracking-tight ${className}`}>
      <LogoIcon size={iconSizes[size]} />
      {!iconOnly && (
        <>
          <span className="font-bold">Unpause</span>
          <span className="font-bold text-accent">AI</span>
        </>
      )}
    </span>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
