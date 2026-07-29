import React from 'react';

/** Hairline-divided disclosure row — the "questions SAP teams actually search" pattern. */
export function FaqRow({ question, children, open = false, onToggle, style, ...rest }) {
  return (
    <div style={{ borderTop: '1px solid var(--border-subtle)', ...style }} {...rest}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 20,
          padding: '20px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          font: 'inherit',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontWeight: 'var(--weight-semibold)',
            fontSize: 17,
            color: 'var(--brisken-ink-900)',
          }}
        >
          {question}
        </span>
        <span style={{ color: 'var(--brisken-teal-600)', fontSize: 18, flex: '0 0 auto' }}>{open ? '−' : '+'}</span>
      </button>
      {open ? (
        <div
          style={{
            paddingBottom: 22,
            maxWidth: 720,
            fontFamily: 'var(--font-sans)',
            fontSize: 15,
            lineHeight: 'var(--leading-body)',
            color: 'var(--brisken-slate-600)',
          }}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}
