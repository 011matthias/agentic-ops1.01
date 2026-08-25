import React from 'react';

/** Century Gothic headline. Regular weight only — size carries the emphasis. */
export function Headline({ children, size = 'm', tone = 'ink', as: Tag = 'h2', style, ...rest }) {
  const fontSize = { xl: 76, l: 56, m: 40, s: 30 }[size] || size;
  const color = tone === 'onDark' ? 'var(--brisken-surface-050)' : 'var(--brisken-ink-900)';
  return (
    <Tag
      style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 'var(--weight-regular)',
        fontSize,
        lineHeight: 'var(--leading-display)',
        letterSpacing: 0,
        color,
        margin: 0,
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
