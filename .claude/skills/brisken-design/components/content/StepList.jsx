import React from 'react';

/** Numbered process list — "WHAT IT DOES, STEP BY STEP". */
export function StepList({ steps, badgeSize = 34, gap = 14, tone = 'ink', style, ...rest }) {
  return (
    <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap, ...style }} {...rest}>
      {steps.map((s, i) => (
        <li key={i} style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div
            style={{
              flex: '0 0 auto',
              width: badgeSize,
              height: badgeSize,
              borderRadius: Math.round(badgeSize * 0.25),
              background: 'var(--brisken-teal-600)',
              color: 'var(--brisken-white)',
              fontFamily: 'var(--font-sans)',
              fontWeight: 'var(--weight-semibold)',
              fontSize: Math.round(badgeSize * 0.4),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {i + 1}
          </div>
          <div
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 15,
              lineHeight: 1.3,
              paddingTop: Math.round(badgeSize * 0.18),
              color: tone === 'onDark' ? 'var(--brisken-surface-050)' : 'var(--brisken-ink-900)',
            }}
          >
            {s}
          </div>
        </li>
      ))}
    </ol>
  );
}
