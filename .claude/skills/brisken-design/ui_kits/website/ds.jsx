/* Web-surface primitives, matching brisken.com: navy type, mono eyebrows, pill buttons,
   white hairline cards. Resolves the design-system bundle when it is available. */
const __ns = (function () {
  for (const k of Object.keys(window)) {
    try {
      const v = window[k];
      if (v && typeof v === 'object' && v.WebEyebrow) return v;
    } catch (e) { /* cross-origin frame proxy */ }
  }
  return {};
})();

const WebEyebrow = __ns.WebEyebrow || function WebEyebrow({ children, pill = false, tone = 'teal', style }) {
  const color = tone === 'onDark' ? 'var(--text-eyebrow-on-dark)' : 'var(--text-eyebrow)';
  const base = {
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    letterSpacing: 'var(--tracking-eyebrow)',
    textTransform: 'uppercase',
    color,
    display: pill ? 'inline-block' : 'block',
  };
  const pilled = pill ? { background: 'var(--surface-eyebrow-pill)', borderRadius: 999, padding: '7px 18px' } : null;
  return <div style={{ ...base, ...pilled, ...style }}>{children}</div>;
};

const WebHeadline = __ns.WebHeadline || function WebHeadline({ children, size = 'l', as: Tag = 'h2', tone = 'ink', style }) {
  const fontSize = { xl: 60, l: 40, m: 30, s: 24 }[size] || size;
  return (
    <Tag style={{
      fontFamily: 'var(--font-display)',
      fontWeight: 600,
      fontSize,
      lineHeight: 1.14,
      letterSpacing: '-0.01em',
      margin: 0,
      color: tone === 'onDark' ? 'var(--brisken-white)' : 'var(--text-primary)',
      ...style,
    }}>{children}</Tag>
  );
};

const WebButton = __ns.WebButton || function WebButton({ children, variant = 'primary', size = 'm', href, style, ...rest }) {
  const pad = size === 's' ? '9px 18px' : size === 'l' ? '16px 34px' : '13px 28px';
  const v = {
    primary: { background: 'var(--brisken-teal-600)', color: '#fff' },
    onDark: { background: '#fff', color: 'var(--brisken-navy-700)' },
    ghost: { background: 'transparent', color: 'var(--text-link)', border: '1px solid var(--text-link)' },
    tag: { background: 'transparent', color: 'var(--text-eyebrow)', border: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)', letterSpacing: '.12em', textTransform: 'uppercase', fontSize: 11 },
  }[variant];
  const Tag = href ? 'a' : 'button';
  return (
    <Tag href={href} style={{
      display: 'inline-flex', alignItems: 'center', gap: 8, padding: pad,
      fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: size === 's' ? 13 : 15,
      lineHeight: 1, borderRadius: 999, border: '1px solid transparent',
      cursor: 'pointer', textDecoration: 'none', ...v, ...style,
    }} {...rest}>{children}</Tag>
  );
};

const WebCard = __ns.WebCard || function WebCard({ children, edge = false, style }) {
  return (
    <div style={{
      background: 'var(--surface-card)',
      border: '1px solid var(--border-subtle)',
      borderLeft: edge ? '3px solid var(--brisken-teal-600)' : '1px solid var(--border-subtle)',
      borderRadius: 12,
      boxShadow: 'var(--shadow-card)',
      padding: 22,
      ...style,
    }}>{children}</div>
  );
};

const WebSection = __ns.WebSection || function WebSection({ id, children, tone = 'page', style }) {
  const bg = { page: 'var(--surface-page)', flat: 'var(--surface-flat)', dark: 'var(--surface-dark)' }[tone];
  return (
    <section id={id} style={{ background: bg, padding: '84px 0', ...style }}>
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '0 32px', textAlign: 'center' }}>{children}</div>
    </section>
  );
};

const WebFaqRow = __ns.WebFaqRow || function WebFaqRow({ question, children, open, onToggle }) {
  return (
    <div style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <button type="button" onClick={onToggle} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 20, padding: '18px 4px', background: 'none', border: 'none', cursor: 'pointer',
        textAlign: 'left', font: 'inherit',
      }}>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 16, color: 'var(--text-primary)' }}>{question}</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 13, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform var(--duration-fast) var(--ease-standard)' }}>&#9662;</span>
      </button>
      {open ? (
        <div style={{ padding: '0 4px 20px', textAlign: 'left', fontSize: 15, lineHeight: 1.6, color: 'var(--text-secondary)' }}>{children}</div>
      ) : null}
    </div>
  );
};
