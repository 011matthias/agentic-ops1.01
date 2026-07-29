import React from 'react';

/** Horizontal run of proof points, middle-dot separated. */
export function CredentialRow({ items, tone = 'light', size = 13, style, ...rest }) {
  const color = tone === 'onDark' ? 'var(--brisken-slate-300)' : 'var(--brisken-slate-400)';
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 14,
        fontFamily: 'var(--font-sans)',
        fontSize: size,
        color,
        ...style,
      }}
      {...rest}
    >
      {items.map((item, i) => (
        <React.Fragment key={i}>
          {i > 0 ? <span aria-hidden="true">·</span> : null}
          {typeof item === 'string' ? <span>{item}</span> : <img src={item.src} alt={item.alt} style={{ height: item.height || 26 }} />}
        </React.Fragment>
      ))}
    </div>
  );
}
