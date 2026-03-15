import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 py-8 sm:flex-row sm:justify-between">
        <p className="text-sm text-muted">
          &copy; {new Date().getFullYear()} UnpauseAI. All rights reserved.
        </p>
        <div className="flex gap-6">
          <Link
            href="/services"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            Services
          </Link>
          <Link
            href="/about"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            About
          </Link>
          <Link
            href="/contact"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            Contact
          </Link>
          <a
            href="mailto:nicolas.neumann@unpauseai.com"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            nicolas.neumann@unpauseai.com
          </a>
        </div>
      </div>
    </footer>
  );
}
