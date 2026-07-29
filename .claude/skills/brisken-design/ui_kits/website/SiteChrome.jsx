/* Sticky header and navy footer, as on brisken.com. */
function SiteHeader({ site, onNavigate, theme, onToggleTheme, onDemo }) {
  const links = site === 'tc'
    ? [['TreasuryCentral', 'treasury-central'], ['OnePilot', 'onepilot'], ['Applications', 'map'], ['Why now', 'why-now']]
    : [['Applications', 'applications'], ['Governed on SAP', 'governed'], ['Answers', 'answers']];
  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 20, background: 'var(--surface-card)', borderBottom: '1px solid var(--border-subtle)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, minHeight: 64, padding: '8px 24px' }}>
        <button onClick={() => onNavigate(site === 'tc' ? 'op' : 'tc')} style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0, flex: '0 0 auto' }}>
          <img src={theme === 'web-dark' ? '../../assets/logos/brisken-logo-reversed.png' : '../../assets/logos/brisken-logo.png'} alt="Brisken" style={{ height: 20 }} />
          <span style={{ width: 1, height: 18, background: 'var(--border-subtle)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
            {site === 'tc' ? 'TreasuryCentral' : 'OnePilot'}
          </span>
        </button>
        <nav style={{ display: 'flex', gap: 24, margin: '0 auto', minWidth: 0, flexWrap: 'wrap', justifyContent: 'center' }}>
          {links.map(([label, id]) => (
            <a key={id} href={'#' + id} style={{ fontSize: 14.5, color: 'var(--text-primary)', textDecoration: 'none', borderBottom: 'none', whiteSpace: 'nowrap' }}>{label}</a>
          ))}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: '0 0 auto' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-eyebrow)', border: '1px solid var(--border-subtle)', borderRadius: 999, padding: '6px 14px', whiteSpace: 'nowrap', flex: '0 0 auto' }}>Live on SAP</span>
          <WebButton size="s" onClick={onDemo} style={{ whiteSpace: 'nowrap', flex: '0 0 auto' }}>More details</WebButton>
          <button onClick={onToggleTheme} title="Light / dark" style={{ flex: '0 0 auto', width: 30, height: 30, borderRadius: 999, border: '1px solid var(--border-subtle)', background: 'none', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 11 }}>
            {theme === 'web-dark' ? '\u263e' : '\u263c'}
          </button>
        </div>
      </div>
    </header>
  );
}

function SiteFooter() {
  const cols = [
    ['Applications', ['Market Data Hub', 'BST, Brisken Smart Trading', 'Remittance Advice Gate', 'Bank Fee Portal', 'AI Digital Workforce']],
    ['Explore', ['The problem', 'TreasuryCentral', 'Applications', 'The OnePilot platform', 'Answers', 'Book a demo']],
  ];
  return (
    <footer style={{ background: 'var(--brisken-navy-900)', color: '#B7C6DA', padding: '56px 0 32px' }}>
      <div style={{ maxWidth: 1160, margin: '0 auto', padding: '0 40px', display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr', gap: 40 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="../../assets/logos/brisken-logo-reversed.png" alt="Brisken" style={{ height: 20 }} />
            <span style={{ width: 1, height: 16, background: 'rgba(255,255,255,.24)' }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.18em', textTransform: 'uppercase', color: '#B7C6DA' }}>OnePilot</span>
          </div>
          <p style={{ fontSize: 14, lineHeight: 1.6, marginTop: 18, maxWidth: 300 }}>
            OnePilot is Brisken&rsquo;s governed, no-code platform for financial data in SAP: market data, trades,
            bank files and remittances into SAP, with a full audit trail.
          </p>
          <a href="https://www.linkedin.com/company/brisken" style={{ fontSize: 14, color: '#7FD3D9', borderBottom: 'none' }}>Brisken on LinkedIn &rarr;</a>
        </div>
        {cols.map(([title, items]) => (
          <div key={title}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.18em', textTransform: 'uppercase', color: '#8296AF' }}>{title}</div>
            <ul style={{ listStyle: 'none', margin: '18px 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: 11 }}>
              {items.map((i) => <li key={i}><a href="#" style={{ fontSize: 14, color: '#DCE6F2', borderBottom: 'none' }}>{i}</a></li>)}
            </ul>
          </div>
        ))}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.18em', textTransform: 'uppercase', color: '#8296AF' }}>Credentials</div>
          <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 11, fontSize: 14 }}>
            {['SAP Co-Innovation Partner', 'ISO 27001', 'SOC 1 Type II'].map((t) => (
              <span key={t} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ width: 12, height: 12, borderRadius: 999, border: '1px solid #7FD3D9', display: 'inline-block' }} />{t}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div style={{ maxWidth: 1160, margin: '40px auto 0', padding: '22px 40px 0', borderTop: '1px solid rgba(255,255,255,.14)', fontSize: 12.5, lineHeight: 1.6, color: '#8296AF' }}>
        <p style={{ maxWidth: 860 }}>
          Privacy: the financial data you connect is processed only to run the services you configure. We do not use it
          to train models and we do not sell it; access is logged and governed end to end.
        </p>
        <p>Brisken LLC · 9595 Six Pines Drive, Bldg 8 Ste 8210, The Woodlands, TX 77380 · Last updated: 2026-07-16</p>
      </div>
    </footer>
  );
}
