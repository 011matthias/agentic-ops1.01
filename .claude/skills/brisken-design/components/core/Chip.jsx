import React from 'react';

/** Bordered or filled label block — source/destination pills, app names, tags. */
export function Chip({ children, variant = 'bordered', align = 'left', style, ...rest }) {
  const variants = {
    bordered: { background: 'var(--brisken-white)', border: '2px solid var(--border-subtle)', color: 'var(--brisken-ink-900)' },
    accent: { background: 'var(--brisken-white)', border: '2px solid var(--brisken-teal-600)', color: 'var(--brisken-teal-600)' },
    filled: { background: 'var(--surface-card)', border: '2px solid transparent', color: 'var(--brisken-ink-900)' },
    dark: { background: 'var(--brisken-ink-900)', border: '2px solid transparent', color: 'var(--brisken-surface-050)' },
  };
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: align === 'center' ? 'center' : 'flex-start',
        textAlign: align,
        padding: '14px 18px',
        borderRadius: 'var(--radius-m)',
        fontFamily: 'var(--font-sans)',
        fontWeight: 'var(--weight-semibold)',
        fontSize: 14,
        lineHeight: 1.2,
        ...variants[variant],
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
