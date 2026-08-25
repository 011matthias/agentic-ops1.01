/* Book a demo dialog, as reached from the header and every CTA. */
function DemoDialog({ open, onClose }) {
  const [sent, setSent] = React.useState(false);
  if (!open) return null;
  const field = (label, type = 'text') => (
    <label key={label} style={{ display: 'flex', flexDirection: 'column', gap: 6, textAlign: 'left' }}>
      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{label}</span>
      <input type={type} style={{ height: 44, padding: '0 14px', border: '1px solid var(--border-subtle)', borderRadius: 8, fontFamily: 'var(--font-sans)', fontSize: 15, background: 'var(--surface-card)', color: 'var(--text-primary)' }} />
    </label>
  );
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(1,57,111,.42)', zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 520, maxHeight: '86vh', overflow: 'auto', background: 'var(--surface-card)', borderRadius: 14, padding: 34, boxShadow: 'var(--shadow-overlay)', textAlign: 'center' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', fontSize: 22, color: 'var(--text-muted)', cursor: 'pointer' }}>&times;</button>
        </div>
        <WebEyebrow>Book a demo</WebEyebrow>
        <WebHeadline size="s" style={{ marginTop: 10 }}>Stop believing, start doing.</WebHeadline>
        {sent ? (
          <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--text-secondary)', marginTop: 18 }}>
            Thank you. We will be in touch to arrange fifteen to twenty minutes on Brisken&rsquo;s own SAP environment.
            No preparation needed.
          </p>
        ) : (
          <React.Fragment>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '14px 0 18px' }}>Fields marked * are required.</p>
            <div style={{ display: 'grid', gap: 16 }}>
              {['Full name *', 'Work email *', 'Company *', 'Preferred date / availability *'].map((l) => field(l))}
              <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13.5, lineHeight: 1.45, color: 'var(--text-secondary)', textAlign: 'left' }}>
                <input type="checkbox" style={{ marginTop: 3, accentColor: 'var(--text-eyebrow)' }} />
                I agree Brisken may store these details to contact me about a demo.
              </label>
              <WebButton onClick={() => setSent(true)}>Request a demo</WebButton>
            </div>
          </React.Fragment>
        )}
      </div>
    </div>
  );
}
