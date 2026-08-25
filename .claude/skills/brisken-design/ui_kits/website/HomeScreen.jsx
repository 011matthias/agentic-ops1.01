/* brisken.com — centred navy layout, mono eyebrows, pill CTAs, node map, FAQ. */
const CUSTOMERS = ['asr-group', 'nike', 'ab-inbev', 'ford', 'siemens-energy', 'yeti', 'zespri', 'adm'];

const MAP_NODES = [
  ['TreasuryCentral', 'the treasury workspace', 'THE COCKPIT', 'TreasuryCentral, powered by OnePilot: one cockpit for the whole treasury', 'Cash, investments, debt, FX, market risk management and governance on one screen, on your SAP data. It is OnePilot scoped to the treasurer; the apps run on OnePilot, which moves the data in and out of SAP, governed end to end.'],
  ['What treasury deals with', 'banks, markets, authorities', 'WHAT TREASURY DEALS WITH', 'Every external service and counterparty, into the workspace', 'Treasury connects to banks, markets and public bodies every day. OnePilot brings each of those feeds onto one governed layer inside the workspace: visible, accessible and reconciled, with the source and the check recorded on every value.'],
  ['Applications', 'the apps in the workspace', 'THE APPLICATIONS', 'The apps, in the workspace', 'Each app is a job you can buy on its own; run them together and you get TreasuryCentral. All run on OnePilot, which moves the data in and out of SAP, governed end to end.'],
  ['What the business runs on', 'SAP and enterprise systems', 'THE FOUNDATION', 'Your SAP applications and data', 'The systems and data it all sits on. OnePilot moves data in and out of SAP, both ways, with a full audit trail on every record, no ABAP and no custom interface for your team to own.'],
  ['Why now', 'the S/4HANA window', 'WHY NOW', 'Your S/4HANA migration is the moment these feeds get decided', 'SAP ends mainstream maintenance for ECC in 2027, with extended maintenance to 2030. Migration is when the custom interfaces feeding market data, curves and bank files into the old system become legacy code the team has to rebuild, or replace with a product.'],
];

function HeroDiagram() {
  const spokes = [
    ['Market data', 8, 26], ['AI', 40, 6], ['Banks', 2, 46],
    ['Files', 6, 74], ['Email', 30, 96], ['ERPs', 58, 96],
  ];
  return (
    <div style={{ position: 'relative', height: 300, width: '100%', maxWidth: 520, marginInline: 'auto' }}>
      {spokes.map(([label, x, y]) => (
        <div key={label} style={{ position: 'absolute', left: x + '%', top: y + '%', transform: 'translate(-50%,-50%)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>{label}</span>
          <span style={{ width: 7, height: 7, borderRadius: 999, border: '1px solid var(--text-eyebrow)' }} />
        </div>
      ))}
      <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', width: 108, height: 108, borderRadius: 16, border: '1px solid var(--text-eyebrow)', background: 'var(--surface-eyebrow-pill)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '.14em', color: 'var(--text-muted)' }}>UNIVERSAL AI</span>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 19, color: 'var(--text-eyebrow)' }}>OnePilot</span>
      </div>
      <div style={{ position: 'absolute', left: '50%', right: 0, top: '50%', height: 1, borderTop: '1px dashed var(--border-subtle)' }} />
      <span style={{ position: 'absolute', left: '68%', top: 'calc(50% - 18px)', fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '.14em', color: 'var(--text-muted)' }}>GOVERNED</span>
      <div style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)', background: 'var(--brisken-navy-700)', color: '#fff', borderRadius: 6, padding: '14px 20px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 17 }}>SAP</div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '.12em', opacity: .8 }}>S/4HANA</div>
      </div>
    </div>
  );
}

function MapDialog({ node, onClose, onStep }) {
  if (!node) return null;
  const i = MAP_NODES.findIndex((n) => n[0] === node[0]);
  const tabs = ['TreasuryCentral', 'Deals with', 'Applications', 'Business runs on', 'Why now'];
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(1,57,111,.42)', zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 760, maxHeight: '76vh', overflow: 'auto', background: 'var(--surface-card)', borderRadius: 14, padding: '26px 40px 40px', textAlign: 'center', boxShadow: 'var(--shadow-overlay)' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, letterSpacing: '.1em', color: 'var(--text-muted)' }}>
          Map <span style={{ color: 'var(--border-subtle)' }}>&rsaquo;</span> <strong style={{ color: 'var(--text-primary)' }}>{node[0]}</strong>
        </div>
        <button onClick={onClose} style={{ marginTop: 16, background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 999, padding: '8px 18px', fontSize: 13.5, cursor: 'pointer', color: 'var(--text-primary)', fontFamily: 'var(--font-sans)' }}>&larr; Back</button>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', margin: '20px 0 26px' }}>
          {tabs.map((t, j) => (
            <button key={t} onClick={() => onStep(j)} style={{
              display: 'flex', gap: 7, alignItems: 'center', padding: '7px 14px', borderRadius: 999, cursor: 'pointer',
              fontFamily: 'var(--font-sans)', fontSize: 12.5,
              background: j === i ? 'var(--brisken-teal-600)' : 'transparent',
              color: j === i ? '#fff' : 'var(--text-primary)',
              border: '1px solid ' + (j === i ? 'var(--brisken-teal-600)' : 'var(--border-subtle)'),
            }}>
              <span style={{ opacity: .7, fontFamily: 'var(--font-mono)', fontSize: 11 }}>{j + 1}</span>{t}
            </button>
          ))}
        </div>
        <WebEyebrow style={{ marginBottom: 12 }}>{node[2]}</WebEyebrow>
        <WebHeadline size="m">{node[3]}</WebHeadline>
        <p style={{ fontSize: 15.5, lineHeight: 1.62, color: 'var(--text-secondary)', maxWidth: 620, margin: '16px auto 0' }}>{node[4]}</p>
      </div>
    </div>
  );
}

function HomeScreen({ onDemo }) {
  const [open, setOpen] = React.useState(-1);
  const [node, setNode] = React.useState(null);
  const faqs = [
    ['How do I get Bloomberg market data into SAP TRM automatically?', 'The SAP-native path is a Datafeed RFC connection with per-provider function lists and translation tables, or a per-security custom interface, both of which need ABAP upkeep and break when Bloomberg changes a field. A governed market-data hub ingests Bloomberg once, normalizes it, and distributes into SAP TRM with an audit trail and exception alerts, no code.'],
    ['How do I automate CAMT.086 bank fee statement analysis in SAP?', 'CAMT.086 is the ISO 20022 bank-fee-statement format that replaces TWIST BSB. SAP added native bank-fee analysis in S/4HANA 1809 via a Fiori app, but it expects clean CAMT.086 in; banks still send proprietary and TWIST formats. A bank-fee portal ingests any format, enriches for analytics, and distributes to the analyzer, so the fee review is not gated on format.'],
    ['Can AI read remittance advice emails and post them into SAP?', 'Yes. Remittance advice arrives as unstructured email and PDF, which staff retype into SAP cash application. An AI-powered remittance gate reads the unstructured input, identifies and structures the data, and delivers it into SAP S/4HANA, with a monitor that trains it over time.'],
    ['Can we deploy AI agents in treasury without consuming our IT budget?', 'Yes. OnePilot is configured, not coded, and runs as a managed product on top of your SAP landscape, so there is no ABAP build and nothing new for your IT team to own or maintain.'],
    ['Is AI automation in treasury safe?', 'It is safe when the AI runs inside your controls rather than around them. Each OnePilot process works to rules you set and approve, with four-eye release, segregation of duties and a full audit trail on every record.'],
    ['Can AI improve liquidity forecasting?', 'Yes. A forecast is only as good as the data feeding it, and most of the delay is in collecting and cleaning cash, bank and exposure data by hand. OnePilot keeps that data current and governed in SAP.'],
    ['Can AI help the team focus the day on what matters?', 'The mundane work is taken off people and put in one governed place, so the day shifts from moving data to using it: deciding, not re-typing.'],
  ];

  return (
    <main>
      {/* HERO */}
      <WebSection id="top" style={{ padding: '64px 0 72px' }}>
        <WebEyebrow pill>Financial-data platform for SAP. Governed, no code.</WebEyebrow>
        <WebHeadline as="h1" size="xl" style={{ margin: '34px auto 0', maxWidth: 900 }}>Financial Data. Solved. End to End.</WebHeadline>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.15fr', gap: 48, alignItems: 'center', marginTop: 64 }}>
          <div>
            <WebEyebrow style={{ marginBottom: 20 }}>Our research</WebEyebrow>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 54, lineHeight: 1, color: 'var(--text-eyebrow)' }}>71%</div>
            <p style={{ fontSize: 15.5, lineHeight: 1.6, color: 'var(--text-secondary)', maxWidth: 300, margin: '18px auto 0' }}>
              of the live SAP treasury job ads describe extensive manual data plumbing into SAP.
            </p>
          </div>
          <HeroDiagram />
        </div>
        <div style={{ marginTop: 56 }}><WebButton size="l" onClick={onDemo}>Book a demo</WebButton></div>
      </WebSection>

      {/* CUSTOMERS + CERTIFICATIONS */}
      <WebSection tone="flat" style={{ padding: '52px 0' }}>
        <WebEyebrow tone="teal">Trusted by teams at</WebEyebrow>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 42, justifyContent: 'center', alignItems: 'center', marginTop: 30, opacity: .92 }}>
          {CUSTOMERS.map((c) => (
            <img key={c} src={'../../assets/customer-logos/' + c + '.png'} alt={c} style={{ height: 34, maxWidth: 130, objectFit: 'contain' }} />
          ))}
        </div>
        <WebEyebrow style={{ marginTop: 44 }}>Platform &amp; certifications</WebEyebrow>
        <div style={{ display: 'flex', gap: 30, justifyContent: 'center', flexWrap: 'wrap', marginTop: 18, fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
          {['SAP Co-Innovation Partner', 'Listed on the SAP Store', 'ISO 27001', 'SOC 1 Type II'].map((t) => (
            <span key={t} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 13, height: 13, borderRadius: 999, border: '1.5px solid var(--text-eyebrow)' }} />{t}
            </span>
          ))}
        </div>
      </WebSection>

      {/* PLATFORM MAP */}
      <WebSection id="map">
        <WebEyebrow>Explore the platform</WebEyebrow>
        <p style={{ fontSize: 16.5, lineHeight: 1.62, color: 'var(--text-secondary)', maxWidth: 620, margin: '22px auto 0' }}>
          It is all <a href="#onepilot">OnePilot</a>, Brisken&rsquo;s governed, no-code platform. TreasuryCentral is the
          treasury workspace inside it: the apps, your counterparties and your enterprise systems, on one governed layer.
          Click the workspace, an app, or the platform to open it.
        </p>
        <button onClick={() => setNode(MAP_NODES[0])} style={{ display: 'block', margin: '48px auto 0', width: 300, background: 'var(--brisken-navy-700)', color: '#fff', border: 'none', borderRadius: 14, padding: '20px 24px', cursor: 'pointer', textAlign: 'left', fontFamily: 'var(--font-sans)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 21 }}>OnePilot</div>
              <div style={{ fontSize: 11.5, opacity: .78, marginTop: 4 }}>the governed field, there is no outside</div>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>Visit &rarr;</span>
          </div>
        </button>
        <div style={{ width: 1, height: 46, borderLeft: '1px dashed var(--border-subtle)', margin: '0 auto' }} />
        <button onClick={() => setNode(MAP_NODES[0])} style={{ display: 'block', margin: '0 auto', width: 220, background: 'var(--surface-card)', border: '1px solid var(--brisken-teal-600)', borderRadius: 14, padding: '16px 20px', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 19, color: 'var(--text-primary)' }}>TreasuryCentral</div>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>the treasury workspace</div>
        </button>
        <div style={{ width: '68%', height: 40, borderTop: '1px dashed var(--border-subtle)', borderLeft: '1px dashed var(--border-subtle)', borderRight: '1px dashed var(--border-subtle)', margin: '12px auto 0' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: -1 }}>
          {MAP_NODES.slice(1).map((n) => (
            <button key={n[0]} onClick={() => setNode(n)} style={{ background: 'var(--surface-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: '18px 14px', cursor: 'pointer', boxShadow: 'var(--shadow-card)', fontFamily: 'var(--font-sans)' }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{n[0]}</div>
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 6 }}>{n[1]}</div>
            </button>
          ))}
        </div>
      </WebSection>

      {/* DARK CTA PANEL */}
      <WebSection style={{ padding: '0 0 84px' }}>
        <div style={{ background: 'var(--brisken-navy-800)', borderRadius: 4, padding: '58px 40px' }}>
          <WebHeadline size="m" tone="onDark">See for yourself: stop believing, start doing</WebHeadline>
          <p style={{ fontSize: 15.5, lineHeight: 1.62, color: '#C7D6E8', maxWidth: 560, margin: '18px auto 0' }}>
            We show OnePilot running live on Brisken&rsquo;s own SAP environment, not slideware. Connecting it to your SAP
            takes a few weeks, so the demo proves it on ours first: fifteen to twenty minutes, no preparation needed.
          </p>
          <div style={{ marginTop: 30 }}><WebButton variant="onDark" onClick={onDemo}>Book a demo</WebButton></div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5, letterSpacing: '.1em', color: '#9FB4CC', marginTop: 30 }}>
            SAP Co-Innovation Partner · ISO 27001 · SOC 1 Type II
          </div>
        </div>
      </WebSection>

      {/* PROOF */}
      <WebSection id="treasury-central" style={{ paddingTop: 0 }}>
        <WebEyebrow>What we do, and the proof</WebEyebrow>
        <WebHeadline size="l" style={{ margin: '18px auto 0', maxWidth: 820 }}>Governed financial-data integration for SAP, proven where it counts</WebHeadline>
        <p style={{ fontSize: 15.5, lineHeight: 1.62, color: 'var(--text-secondary)', maxWidth: 700, margin: '20px auto 0' }}>
          Our credentials are real: SAP Co-Innovation Partner and PartnerEdge member, part of SAP Industry Cloud for
          Financial Services and Commodities, listed on the SAP Store, ISO 27001 and SOC 1 Type II, with data partners
          including Bloomberg, Refinitiv, CME Group, 360T, Deutsche Boerse and OANDA. A financial-services group on
          S/4HANA Public Cloud already governs several data domains from one OnePilot deployment.
        </p>
        <div style={{ display: 'flex', gap: 18, justifyContent: 'center', marginTop: 28 }}>
          <img src="../../assets/badges/aicpa-soc.png" alt="AICPA SOC 1 Type II certified" style={{ height: 78 }} />
          <img src="../../assets/badges/iso-27001-certified.png" alt="ISO/IEC 27001 certified" style={{ height: 78 }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 32, textAlign: 'center' }}>
          {[['Agricultural customer', 'Posts remittances into S/4HANA on a governed AI gate.'],
            ['Chemicals customer', 'Runs an AI funding-request process across a complex SAP integration.']].map(([t, d]) => (
            <WebCard key={t} edge>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-eyebrow)' }}>Live today</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 16, color: 'var(--text-primary)', marginTop: 8 }}>{t}</div>
              <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-secondary)', marginTop: 8 }}>{d}</div>
            </WebCard>
          ))}
        </div>
      </WebSection>

      {/* ANSWERS */}
      <WebSection id="answers" style={{ paddingTop: 0 }}>
        <WebEyebrow>Answers</WebEyebrow>
        <WebHeadline size="l" style={{ margin: '16px auto 34px' }}>The questions SAP teams actually search</WebHeadline>
        <div style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {faqs.map(([q, a], i) => (
            <WebFaqRow key={q} question={q} open={open === i} onToggle={() => setOpen(open === i ? -1 : i)}>{a}</WebFaqRow>
          ))}
        </div>
      </WebSection>

      <MapDialog node={node} onClose={() => setNode(null)} onStep={(j) => setNode(MAP_NODES[j])} />
    </main>
  );
}
