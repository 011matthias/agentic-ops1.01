"use client";

import Link from "next/link";
import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import ThemeToggle from "./ThemeToggle";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/services", label: "Services" },
  { href: "/automations", label: "Automations" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { data: session } = useSession();

  return (
    <header className="border-b border-border">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          UnpauseAI
        </Link>

        {/* Desktop nav */}
        <ul className="hidden gap-8 sm:flex items-center">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="text-sm text-muted transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li>
            <ThemeToggle />
          </li>
          <li>
            {session ? (
              <div className="flex items-center gap-4">
                <Link
                  href="/portal"
                  className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Portal
                </Link>
                <button
                  onClick={() => signOut({ callbackUrl: "/" })}
                  className="text-sm text-muted transition-colors hover:text-foreground"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="text-sm px-4 py-1.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-700 dark:hover:bg-gray-100 transition-colors"
              >
                Login
              </Link>
            )}
          </li>
        </ul>

        {/* Mobile menu button */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="sm:hidden"
          aria-label="Toggle menu"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            {menuOpen ? (
              <path d="M18 6L6 18M6 6l12 12" />
            ) : (
              <path d="M3 12h18M3 6h18M3 18h18" />
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile nav */}
      {menuOpen && (
        <ul className="border-t border-border px-6 py-4 sm:hidden">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="block py-2 text-sm text-muted transition-colors hover:text-foreground"
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li className="pt-2">
            <ThemeToggle className="w-full justify-start" />
          </li>
          <li className="pt-2">
            {session ? (
              <>
                <Link
                  href="/portal"
                  className="block py-2 text-sm font-medium text-blue-600 dark:text-blue-400"
                  onClick={() => setMenuOpen(false)}
                >
                  Portal
                </Link>
                <button
                  onClick={() => { setMenuOpen(false); signOut({ callbackUrl: "/" }) }}
                  className="block py-2 text-sm text-muted hover:text-foreground"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="block py-2 text-sm font-medium text-foreground"
                onClick={() => setMenuOpen(false)}
              >
                Login
              </Link>
            )}
          </li>
        </ul>
      )}
    </header>
  );
}
