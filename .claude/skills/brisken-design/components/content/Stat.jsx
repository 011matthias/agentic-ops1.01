import React from 'react';

/** A sourced number. Brisken never shows a figure without its attribution. */
export function Stat({ value, children, source, tone = 'ink', style, ...rest }) {
  const onDark = tone === 'onDark';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, ...style }} {...rest}>
      <div
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 44,
          lineHeight: 1,
          color: onDark ? 'var(--brisken-teal-400)' : 'var(--brisken-teal-600)',
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 15,
          lineHeight: 1.3,
          color: onDark ? 'var(--brisken-surface-050)' : 'var(--brisken-ink-900)',
        }}
      >
        {children}
      </div>
      {source ? (
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--brisken-slate-400)' }}>{source}</div>
      ) : null}
    </div>
  );
}
