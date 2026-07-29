import React from 'react';

/** Hairline + "TreasuryCentral, powered by OnePilot" left, slide number right. */
export function SlideFooter({ label = 'TreasuryCentral, powered by OnePilot', page, scale = 1, style, ...rest }) {
  return (
    <div style={{ ...style }} {...rest}>
      <div style={{ height: 2 * scale, background: 'var(--border-subtle)' }} />
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          paddingTop: 12 * scale,
          fontFamily: 'var(--font-sans)',
          fontSize: 18 * scale,
          color: 'var(--brisken-slate-400)',
        }}
      >
        <span style={{ letterSpacing: 'var(--tracking-footer)' }}>{label}</span>
        <span>{page}</span>
      </div>
    </div>
  );
}
