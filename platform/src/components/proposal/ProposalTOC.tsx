"use client";

import { useEffect, useState } from "react";

interface Heading {
  id: string;
  text: string;
  level: 2 | 3;
}

interface ProposalTOCProps {
  headings: Heading[];
}

export function ProposalTOC({ headings }: ProposalTOCProps) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: "0px 0px -75% 0px", threshold: 0 }
    );

    for (const h of headings) {
      const el = document.getElementById(h.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [headings]);

  function handleClick(e: React.MouseEvent<HTMLAnchorElement>, id: string) {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
      window.history.replaceState(null, "", `#${id}`);
    }
  }

  return (
    <nav className="proposal-toc-sidebar" aria-label="Table of contents">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">
        On this page
      </p>
      <ul className="space-y-1">
        {headings.map((h) => (
          <li key={h.id}>
            <a
              href={`#${h.id}`}
              onClick={(e) => handleClick(e, h.id)}
              className={`block text-sm py-1 transition-colors duration-150 border-l-2 ${
                h.level === 3 ? "pl-5" : "pl-3"
              } ${
                activeId === h.id
                  ? "border-accent text-accent font-medium"
                  : "border-transparent text-muted hover:text-foreground hover:border-border"
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function ProposalTOCMobile({ headings }: ProposalTOCProps) {
  function handleClick(e: React.MouseEvent<HTMLAnchorElement>, id: string) {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <details className="proposal-toc-mobile lg:hidden mb-8 rounded-lg border border-border bg-surface p-4">
      <summary className="cursor-pointer text-sm font-semibold text-foreground select-none">
        On this page
      </summary>
      <ul className="mt-3 space-y-1">
        {headings.map((h) => (
          <li key={h.id}>
            <a
              href={`#${h.id}`}
              onClick={(e) => handleClick(e, h.id)}
              className={`block text-sm py-0.5 text-muted hover:text-accent transition-colors ${
                h.level === 3 ? "pl-4" : ""
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}
