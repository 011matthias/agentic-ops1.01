import React from 'react';

/** Filled teal rounded square with a white numeral — the brand's step marker. */
export function NumberBadge({ n, size = 34, tone = 'teal', style, ...rest }) {
  const bg = tone === 'ink' ? 'var(--brisken-ink-900)' : 'var(--brisken-teal-600)';
  return (
    <div
      style={{
        flex: '0 0 auto',
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.25),
        background: bg,
        color: 'var(--brisken-white)',
        fontFamily: 'var(--font-sans)',
        fontWeight: 'var(--weight-semibold)',
        fontSize: Math.round(size * 0.4),
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...style,
      }}
      {...rest}
    >
      {n}
    </div>
  );
}
