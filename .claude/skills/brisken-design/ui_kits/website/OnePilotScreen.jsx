/* onepilot.brisken.com — same chrome, same centred navy system. */
function OnePilotScreen({ onDemo }) {
  const apps = [
    ['BST, Brisken Smart Trading', 'FX and trade execution on the surface, logged and governed back into SAP.', 'Flagship, live on SAP'],
    ['Market Data Hub', 'Brings live market data into SAP, in the context where the decision is made.', 'Live on SAP'],
    ['Remittance Advice Gate', 'An agent reads remittances and structures them into SAP cash application, with no re-keying.', 'Live on SAP'],
    ['Bank Fee Portal', 'Bank-fee transparency and analysis, the charges checked against what was agreed.', 'Live on SAP'],
    ['AI Digital Workforce', 'Permissioned agents that do the repetitive treasury work by exception, inside your access.', 'Live on SAP'],
    ['Executive cockpit', 'One read across the business: finance, sales and operations in a single governed view.', 'Illustration'],
  ];
  const day = [
    ['07:30', 'Morning cash position', 'Log in to two bank portals and SAP, export, reconcile balances by hand in a spreadsheet.', 'Cash across banks and SAP, reconciled overnight by exception, on the surface when you sit down.'],
    ['Daily', 'Payment runs, without the keying', 'Remittances retyped into cash application, payments keyed and chased across systems.', 'The agent reads remittances, structures them into SAP, and stages the run; you release under four-eye.'],
    ['Month-end', 'The board pack, drafted', 'Pull figures from five places, paste into slides, format to the template, version by email.', 'The agent pulls the figures and drafts the pack to your template; you review and adjust.'],
    ['In the moment', 'FX execution in context', 'Switch to the trading platform, check exposure in another tab, execute, log it back by hand.', 'Exposure, market data and execution on the same surface, the action logged automatically.'],
  ];
  return (
    <main>
      <WebSection style={{ padding: '64px 0 72px' }}>
        <WebEyebrow pill>The Universal UI from Brisken</WebEyebrow>
        <WebHeadline as="h1" size="xl" style={{ margin: '32px auto 0', maxWidth: 880 }}>Your whole working day, in orbit around one surface.</WebHeadline>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: 'var(--text-secondary)', maxWidth: 660, margin: '22px auto 0' }}>
          OnePilot is the surface and framework. TreasuryCentral is its one shipped edition, live on SAP.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginTop: 56 }}>
          {[['~1,200', 'app and site switches the average worker makes in a day.', 'Harvard Business Review, 2022'],
            ['up to 40%', 'of productive time lost to switching between disconnected apps.', 'American Psychological Association'],
            ['~340', 'SaaS apps in a large enterprise, so any single-suite answer is partial.', 'Productiv, State of SaaS, 2024']].map(([v, d, s]) => (
            <WebCard key={v}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 32, color: 'var(--text-eyebrow)' }}>{v}</div>
              <div style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--text-primary)', marginTop: 10 }}>{d}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>{s}</div>
            </WebCard>
          ))}
        </div>
      </WebSection>

      <WebSection id="applications" tone="flat">
        <WebEyebrow>Applications</WebEyebrow>
        <WebHeadline size="l" style={{ margin: '16px auto 0' }}>On SAP today, and beyond it</WebHeadline>
        <p style={{ fontSize: 15.5, lineHeight: 1.62, color: 'var(--text-secondary)', maxWidth: 700, margin: '20px auto 0' }}>
          <strong style={{ color: 'var(--text-primary)' }}>OnePilot is not limited to SAP, or to finance.</strong>{' '}
          The platform composes whatever a team works with, from wherever they have access: ERP, banking, market data,
          email, Teams, spreadsheets, anything with an API. One governed surface across all of it, one login and one
          audit trail instead of ten tabs and ten passwords.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginTop: 34, textAlign: 'left' }}>
          {apps.map(([t, d, tag]) => (
            <WebCard key={t} edge={tag !== 'Illustration'}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15.5, color: 'var(--text-primary)' }}>{t}</div>
              <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-secondary)', marginTop: 8 }}>{d}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.14em', textTransform: 'uppercase', marginTop: 12, color: tag === 'Illustration' ? 'var(--text-muted)' : 'var(--text-eyebrow)' }}>{tag}</div>
            </WebCard>
          ))}
        </div>
      </WebSection>

      <WebSection id="governed">
        <WebEyebrow>Governance</WebEyebrow>
        <WebHeadline size="l" style={{ margin: '16px auto 0' }}>Governed on SAP, end to end</WebHeadline>
        <p style={{ fontSize: 15.5, lineHeight: 1.62, color: 'var(--text-secondary)', maxWidth: 660, margin: '20px auto 0' }}>
          An agent reaches exactly what the person it works for can reach, and nothing else. The controls a regulated
          finance team needs are built into the surface.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginTop: 34, textAlign: 'left' }}>
          {[['Permission-bound agents', 'An agent sees and acts only on what the user is allowed to. Access outside that boundary is not dimmed, it is absent.'],
            ['Four-eye and segregation of duties', 'Approvals and separation of duties on the actions that need them. The agent prepares; a person releases.'],
            ['Full audit trail', 'Every record is traceable. You manage by exception, and nothing moves outside the rules you set.']].map(([t, d]) => (
            <WebCard key={t} edge>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15.5, color: 'var(--text-primary)' }}>{t}</div>
              <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-secondary)', marginTop: 8 }}>{d}</div>
            </WebCard>
          ))}
        </div>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5, letterSpacing: '.06em', color: 'var(--text-muted)', marginTop: 30 }}>
          It orchestrates; it does not become the system of record. The book of record stays in SAP.
        </p>
      </WebSection>

      <WebSection tone="flat">
        <WebEyebrow>The treasurer&rsquo;s day, before and on OnePilot</WebEyebrow>
        <WebHeadline size="l" style={{ margin: '16px auto 34px', maxWidth: 720 }}>Each task moves from a string of logins to one glance.</WebHeadline>
        <div style={{ borderTop: '1px solid var(--border-subtle)', textAlign: 'left' }}>
          {day.map(([when, what, today, onOP]) => (
            <div key={what} style={{ display: 'grid', gridTemplateColumns: '160px 1fr 1fr', gap: 28, padding: '22px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{when}</div>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15, marginTop: 8, color: 'var(--text-primary)' }}>{what}</div>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.14em', color: 'var(--text-muted)' }}>TODAY</div>
                <p style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--text-secondary)', margin: '8px 0 0' }}>{today}</p>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.14em', color: 'var(--text-eyebrow)' }}>ON ONEPILOT</div>
                <p style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--text-primary)', margin: '8px 0 0' }}>{onOP}</p>
              </div>
            </div>
          ))}
        </div>
      </WebSection>

      <WebSection id="answers" style={{ paddingTop: 0 }}>
        <div style={{ background: 'var(--brisken-navy-800)', borderRadius: 4, padding: '58px 40px' }}>
          <WebHeadline size="m" tone="onDark">See it running on SAP</WebHeadline>
          <p style={{ fontSize: 15.5, lineHeight: 1.62, color: '#C7D6E8', maxWidth: 560, margin: '18px auto 0' }}>
            TreasuryCentral is live with customers on SAP today. Watch the surface run a money-critical job end to end,
            or reach the team to arrange a walkthrough.
          </p>
          <div style={{ marginTop: 30 }}><WebButton variant="onDark" onClick={onDemo}>Contact us</WebButton></div>
        </div>
      </WebSection>
    </main>
  );
}
