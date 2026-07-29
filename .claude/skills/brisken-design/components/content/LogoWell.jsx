import React from 'react';

/** Flat grey well holding a customer or partner mark, centred and contained. */
export function LogoWell({ src, alt, height = 64, pad = 14, style, ...rest }) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderRadius: 'var(--radius-m)',
        height,
        padding: pad,
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...style,
      }}
      {...rest}
    >
      {src ? (
        <img src={src} alt={alt || ''} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
      ) : (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--brisken-slate-400)' }}>{alt}</span>
      )}
    </div>
  );
}
