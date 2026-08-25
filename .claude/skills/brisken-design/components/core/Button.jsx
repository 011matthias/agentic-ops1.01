import React from 'react';

/** Brisken button. Solid teal is the only primary; ghost is a hairline outline. */
export function Button({ children, variant = 'primary', size = 'm', href, style, ...rest }) {
  const pad = size === 's' ? '9px 16px' : size === 'l' ? '16px 30px' : '13px 24px';
  const fontSize = size === 's' ? 13 : size === 'l' ? 17 : 15;
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    padding: pad,
    fontFamily: 'var(--font-sans)',
    fontWeight: 'var(--weight-semibold)',
    fontSize,
    lineHeight: 1,
    borderRadius: 'var(--radius-s)',
    border: '2px solid transparent',
    cursor: 'pointer',
    textDecoration: 'none',
    transition: 'background var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)',
  };
  const variants = {
    primary: { background: 'var(--brisken-teal-600)', color: 'var(--brisken-white)' },
    ghost: { background: 'transparent', color: 'var(--brisken-teal-600)', borderColor: 'var(--border-subtle)' },
    onDark: { background: 'var(--brisken-teal-400)', color: 'var(--brisken-ink-900)' },
    quiet: { background: 'transparent', color: 'var(--brisken-slate-600)', padding: 0, border: 'none' },
  };
  const Tag = href ? 'a' : 'button';
  return (
    <Tag href={href} style={{ ...base, ...variants[variant], ...style }} {...rest}>
      {children}
    </Tag>
  );
}
