import React from 'react';

/** ALL-CAPS tracked label that opens every Brisken slide and section. */
export function Eyebrow({ children, tone = 'teal', size = 12, as: Tag = 'div', style, ...rest }) {
  const color = {
    teal: 'var(--brisken-teal-600)',
    bright: 'var(--brisken-teal-400)',
    muted: 'var(--brisken-slate-400)',
  }[tone];
  return (
    <Tag
      style={{
        fontFamily: 'var(--font-sans)',
        fontWeight: 'var(--weight-semibold)',
        fontSize: size,
        letterSpacing: 'var(--tracking-eyebrow)',
        textTransform: 'uppercase',
        color,
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
