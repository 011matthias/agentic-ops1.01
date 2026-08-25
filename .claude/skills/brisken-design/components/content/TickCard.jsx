import React from 'react';

/** The signature Brisken card: flat grey fill, short teal tick, title, body. */
export function TickCard({ title, children, accent = 'teal', tone = 'light', pad = 28, style, ...rest }) {
  const tick = accent === 'bright' ? 'var(--brisken-teal-400)' : 'var(--brisken-teal-600)';
  const dark = tone === 'dark';
  return (
    <div
      style={{
        background: dark ? 'var(--brisken-ink-900)' : 'var(--surface-card)',
        borderRadius: 'var(--radius-card)',
        padding: pad,
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        ...style,
      }}
      {...rest}
    >
      <div style={{ width: 49, height: 7, background: tick, flex: '0 0 auto' }} />
      {title ? (
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontWeight: 'var(--weight-semibold)',
            fontSize: 18,
            lineHeight: 1.2,
            color: dark ? 'var(--brisken-surface-050)' : 'var(--brisken-ink-900)',
          }}
        >
          {title}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 15,
          lineHeight: 'var(--leading-card)',
          color: dark ? 'var(--brisken-slate-300)' : 'var(--brisken-slate-600)',
        }}
      >
        {children}
      </div>
    </div>
  );
}
