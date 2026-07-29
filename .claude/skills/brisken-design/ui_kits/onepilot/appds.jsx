/* OnePilot product primitives — the dark app surface.
   Icons are Lucide (CDN), the closest match to the product's thin line icons;
   see readme.md ICONOGRAPHY for the flag on this substitution. */
function Icon({ name, size = 16, color = 'currentColor', style }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (window.lucide && ref.current) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      ref.current.appendChild(el);
      window.lucide.createIcons({
        attrs: { width: size, height: size, stroke: color, 'stroke-width': 1.6 },
        nameAttr: 'data-lucide',
      });
    }
  }, [name, size, color]);
  return <span ref={ref} style={{ display: 'inline-flex', width: size, height: size, ...style }} />;
}

function AppButton({ children, variant = 'ghost', icon, style, ...rest }) {
  const v = {
    ghost: { background: 'transparent', color: 'var(--op-text)', border: '1px solid var(--op-border)' },
    filled: { background: 'var(--op-input)', color: 'var(--op-text)', border: '1px solid transparent' },
    accent: { background: 'transparent', color: 'var(--op-accent)', border: '1px solid var(--op-accent)' },
    chip: { background: 'var(--op-accent)', color: '#fff', border: '1px solid transparent' },
  }[variant];
  return (
    <button style={{
      display: 'inline-flex', alignItems: 'center', gap: 9, padding: '10px 18px', borderRadius: 999,
      fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 700, cursor: 'pointer', lineHeight: 1,
      ...v, ...style,
    }} {...rest}>
      {icon ? <Icon name={icon} size={15} /> : null}{children}
    </button>
  );
}

function IconButton({ name, title, onClick }) {
  return (
    <button title={title} onClick={onClick} style={{
      width: 38, height: 38, borderRadius: 999, background: 'transparent', border: 'none',
      color: 'var(--op-accent)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <Icon name={name} size={20} />
    </button>
  );
}

function AppCard({ title, children, style }) {
  return (
    <div style={{ background: 'var(--op-surface)', border: '1px solid var(--op-border)', borderRadius: 10, padding: 20, ...style }}>
      {title ? <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 15.5, color: 'var(--op-text)', marginBottom: 16 }}>{title}</div> : null}
      {children}
    </div>
  );
}

function DataTable({ columns, rows, sortedBy }) {
  return (
    <div style={{ background: 'var(--op-surface)', border: '1px solid var(--op-border)', borderRadius: 10, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-sans)', fontSize: 13.5 }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} style={{ textAlign: 'left', padding: '16px 20px', fontWeight: 700, color: 'var(--op-text)', borderBottom: '1px solid var(--op-border)', whiteSpace: 'nowrap' }}>
                {c}{sortedBy === c ? <span style={{ color: 'var(--op-text-muted)' }}> &darr;</span> : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ background: i % 2 ? 'rgba(255,255,255,.015)' : 'transparent' }}>
              {r.map((cell, j) => (
                <td key={j} style={{ padding: '15px 20px', borderBottom: '1px solid rgba(255,255,255,.05)', color: cell && cell.tone === 'pos' ? 'var(--op-positive)' : cell && cell.tone === 'neg' ? 'var(--op-negative)' : 'var(--op-text)', fontFamily: cell && cell.mono ? 'var(--font-mono)' : 'var(--font-sans)' }}>
                  {cell && typeof cell === 'object' ? cell.v : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* Pie built from a conic-gradient — the product charts are flat, labelled slices. */
function Pie({ title, slices, size = 220 }) {
  let acc = 0;
  const stops = slices.map((s) => {
    const from = acc; acc += s.pct;
    return s.color + ' ' + from + '% ' + acc + '%';
  }).join(', ');
  const biggest = slices.reduce((a, b) => (b.pct > a.pct ? b : a));
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13.5, color: 'var(--op-text)', marginBottom: 14 }}>{title}</div>
      <div style={{ position: 'relative', width: size, height: size, margin: '0 auto', borderRadius: '50%', background: 'conic-gradient(' + stops + ')', border: '1px solid rgba(255,255,255,.35)' }}>
        <span style={{ position: 'absolute', left: '58%', top: '62%', background: 'rgba(0,0,0,.72)', color: '#fff', fontFamily: 'var(--font-sans)', fontSize: 11.5, fontWeight: 700, padding: '2px 6px', borderRadius: 3 }}>
          {biggest.pct.toFixed(1)}%
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', justifyContent: 'center', marginTop: 18 }}>
        {slices.map((s) => (
          <span key={s.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11.5, color: 'var(--op-text-muted)' }}>
            <span style={{ width: 9, height: 9, borderRadius: 999, background: s.color }} />{s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
