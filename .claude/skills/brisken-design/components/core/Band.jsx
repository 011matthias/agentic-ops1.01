import React from 'react';

/** Full-width summary strip that closes a slide or section. */
export function Band({ children, sub, tone = 'ink', align = 'left', style, ...rest }) {
  const tones = {
    ink: { background: 'var(--brisken-ink-900)', color: 'var(--brisken-surface-050)' },
    teal: { background: 'var(--brisken-teal-600)', color: 'var(--brisken-white)' },
    deep: { background: 'var(--brisken-teal-800)', color: 'var(--brisken-white)' },
    quiet: { background: 'var(--surface-card)', color: 'var(--brisken-ink-900)' },
  };
  return (
    <div
      style={{
        borderRadius: 'var(--radius-s)',
        padding: '18px 24px',
        fontFamily: 'var(--font-sans)',
        fontSize: 14,
        lineHeight: 1.35,
        textAlign: align,
        ...tones[tone],
        ...style,
      }}
      {...rest}
    >
      <div style={{ fontWeight: 'var(--weight-semibold)' }}>{children}</div>
      {sub ? (
        <div style={{ marginTop: 4, opacity: 0.72, fontWeight: 'var(--weight-regular)' }}>{sub}</div>
      ) : null}
    </div>
  );
}
