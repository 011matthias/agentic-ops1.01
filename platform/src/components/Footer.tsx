import Link from "next/link";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="flex flex-col gap-8 sm:flex-row sm:justify-between">
          {/* Brand */}
          <div className="flex flex-col gap-2">
            <Logo size="sm" href="/" />
            <p className="text-sm text-muted">
              Custom automation solutions for your business.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-16">
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium uppercase tracking-wider text-muted">
                Company
              </p>
              <Link
                href="/about"
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                About
              </Link>
              <Link
                href="/services"
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                Services
              </Link>
              <Link
                href="/contact"
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                Contact
              </Link>
            </div>

            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium uppercase tracking-wider text-muted">
                Legal
              </p>
              <Link
                href="/terms"
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                Terms of Service
              </Link>
              <Link
                href="/privacy"
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                Privacy Policy
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 flex flex-col items-center gap-2 border-t border-border pt-6 sm:flex-row sm:justify-between">
          <p className="text-xs text-muted">
            &copy; {new Date().getFullYear()} UnpauseAI. All rights reserved.
          </p>
          <a
            href="mailto:nicolas.neumann@unpauseai.com"
            className="text-xs text-muted transition-colors hover:text-foreground"
          >
            nicolas.neumann@unpauseai.com
          </a>
        </div>
      </div>
    </footer>
  );
}
