/* The three product views in the screenshots: a welcome home, an audit log, and the
   Investment Dashboard. */
function HomeView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 400, fontSize: 40, color: 'var(--op-text)' }}>
        Welcome to Market Data Hub (DEMO)
      </div>
    </div>
  );
}

const AUDIT_ROWS = [
  ['ND38gMIckXIWoJ39RGYZn', 'GBPZWG.M12C'], ['YrXSR9rqe77SI6BGwO5r7', 'GBPZAR.M12C'],
  ['cQLynEZ-C6Y5MYX2C6KGg', 'GBPYER.M12C'], ['-FcOD4y6lAOpQWBdjNHif', 'GBPXPF.M12C'],
  ['zQDOtdfRZUwzCoajsykA8', 'GBPXCD.M12C'], ['8JOFpx9TZKYIHcErHfbzo', 'GBPXAF.M12C'],
  ['uRnkKaiLnDJS8OXIJAIKsC', 'GBPWST.M12C'], ['BYb_WzmpvT4H2fHTjy1fG', 'GBPVND.M12C'],
  ['B6KxqHJAwxLg2I_LCop6I', 'GBPVES.M12C'], ['Z2lhspami7TDC2_qHHfnp', 'GBPV00.M12C'],
  ['kroCtXo5bEWrkdbOPaIc7', 'GBPUYU.M12C'], ['hYJhAVIRDCsoDk-BeQQKO', 'GBPUSD.M12C'],
];

function AuditView({ title }) {
  return (
    <div style={{ padding: '8px 28px 28px', overflow: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20 }}>
        <AppButton icon="filter">Filter</AppButton>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <IconButton name="refresh-cw" title="Refresh" />
          <IconButton name="file-down" title="Export" />
        </div>
      </div>
      <DataTable
        sortedBy="Changed At"
        columns={['Version', 'Change Type', 'Status', 'Changed At', 'Changed By', 'Identifier']}
        rows={AUDIT_ROWS.map(([v, id]) => [
          { v, mono: true }, 'update', 'approved', 'Mar 20, 2026 at 08:24 PM', 'system', { v: id, mono: true },
        ])}
      />
    </div>
  );
}

const POSITIONS = [
  ['Variance Treasury Select Fund', 'USD', '$4,666,990,733', '$1,947,639', '+$4,665,043,094', 5],
  ['Variance Euro Liquidity Fund', 'EUR', '\u20ac2,757,574,175', '\u20ac2,788,099', '+\u20ac2,754,786,076', 6],
  ['Variance Liquidity Reserve Fund', 'USD', '$2,001,901,199', '$1,259,896', '+$2,000,641,303', 7],
  ['Variance Government Cash Fund', 'USD', '$931,575,689', '$1,748,666', '+$929,827,023', 7],
  ['Variance Euro Short Duration', 'EUR', '\u20ac584,506,122', '\u20ac5,437,361', '+\u20ac579,068,761', 6],
  ['FEDSEUA', 'USD', '$98,785,098', '$12,149,348', '+$86,635,749', 18],
  ['FEDSTPI', 'EUR', '\u20ac378,390', '\u20ac25', '+\u20ac378,365', 6],
  ['Federated Short', 'EUR', '\u20ac12,345', '\u20ac0', '+\u20ac12,345', 1],
  ['Federated Hermes Govt Obli IS', 'USD', '$2,222', '$0', '+$2,222', 2],
  ['UTIXX', 'USD', '$1,230', '$81', '+$1,149', 2],
];

function InvestmentView() {
  const [tab, setTab] = React.useState('Overview');
  return (
    <div style={{ padding: '8px 28px 28px', overflow: 'auto' }}>
      <div style={{ background: 'var(--op-surface)', border: '1px solid var(--op-border)', borderRadius: 10, padding: 20 }}>
        <div style={{ display: 'flex', gap: 28, borderBottom: '1px solid var(--op-border)', marginBottom: 24 }}>
          {['Overview', 'Requests'].map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px 14px',
              fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 700,
              color: tab === t ? 'var(--op-accent)' : 'var(--op-text-muted)',
              borderBottom: '2px solid ' + (tab === t ? 'var(--op-accent)' : 'transparent'),
              marginBottom: -1,
            }}>{t}</button>
          ))}
        </div>

        {tab === 'Overview' ? (
          <React.Fragment>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <AppCard title="Net Position by Product">
                <Pie title="USD" slices={[
                  { label: 'FEDSINS', pct: 41.6, color: 'var(--op-chart-1)' },
                  { label: 'Variance Treasury Select Fund', pct: 35.5, color: 'var(--op-chart-2)' },
                  { label: 'Variance Liquidity Reserve Fund', pct: 15.2, color: 'var(--op-chart-3)' },
                  { label: 'Variance Government Cash Fund', pct: 7.1, color: 'var(--op-chart-4)' },
                ]} />
                <div style={{ height: 28 }} />
                <Pie title="EUR" slices={[
                  { label: 'Variance Euro Liquidity Fund', pct: 82.6, color: '#1A4F8B' },
                  { label: 'Variance Euro Short Duration', pct: 17.4, color: 'var(--op-chart-2)' },
                ]} />
              </AppCard>
              <AppCard title="Position Timeline">
                <div style={{ height: 300, position: 'relative', paddingLeft: 60 }}>
                  {[15000, 10000, 5000, 0].map((v, i) => (
                    <div key={v} style={{ position: 'absolute', left: 0, right: 0, top: (i * 30) + '%', display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ width: 52, textAlign: 'right', fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--op-text-muted)' }}>{v.toFixed(1)}M</span>
                      <span style={{ flex: 1, borderTop: '1px dashed rgba(255,255,255,.14)' }} />
                    </div>
                  ))}
                  <svg viewBox="0 0 400 200" preserveAspectRatio="none" style={{ position: 'absolute', left: 60, right: 0, top: 0, bottom: 40, width: 'calc(100% - 60px)', height: 'calc(100% - 40px)' }}>
                    <polyline points="0,190 200,190 200,120 330,120 330,120 400,120" fill="none" stroke="var(--op-chart-2)" strokeWidth="2" />
                    <polyline points="0,192 250,192 250,150 360,150 360,20 400,20" fill="none" stroke="var(--op-chart-1)" strokeWidth="2" />
                  </svg>
                  <div style={{ position: 'absolute', left: 60, right: 0, bottom: 0, display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 9.5, color: 'var(--op-text-muted)' }}>
                    {['2024-03-01', '2025-05-01', '2025-08-28', '2025-11-14', '2026-01-21'].map((d) => (
                      <span key={d} style={{ transform: 'rotate(-40deg)', transformOrigin: 'left top' }}>{d}</span>
                    ))}
                  </div>
                </div>
              </AppCard>
            </div>
            <div style={{ marginTop: 20 }}>
              <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 15.5, color: 'var(--op-text)', marginBottom: 14 }}>Positions by Product</div>
              <DataTable
                columns={['Variance', 'Currency', 'Gross Purchases', 'Gross Redemptions', 'Net Position', 'Requests']}
                rows={POSITIONS.map(([name, ccy, buy, sell, net, req]) => [
                  name, { v: ccy, mono: true }, { v: buy, mono: true }, { v: sell, mono: true, tone: 'neg' },
                  { v: net, mono: true, tone: 'pos' }, req,
                ])}
              />
            </div>
          </React.Fragment>
        ) : (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--op-text-muted)', fontSize: 14.5 }}>
            No investment requests in the selected window.
          </div>
        )}
      </div>
    </div>
  );
}
