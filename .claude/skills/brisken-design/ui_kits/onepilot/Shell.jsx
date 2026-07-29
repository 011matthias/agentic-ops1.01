/* Sidebar + top bar. The sidebar is a searchable list of spaces, grouped, with the signed-in
   user pinned to the bottom. */
const SPACE_GROUPS = [
  ['Audit', ['API Settings Audit', 'Approval Policies Audit Log', 'BAT Rates Integration', 'BAT Target Audit Log', 'Calendars Audit Log', 'Classes Audit Log', 'Collection Admin Audit Log', 'Countries Audit Log', 'Currencies Audit Log', 'Event Subscription Audit', 'Function Composer Audit Log', 'Instrument Group Audit Log', 'Instruments Audit Log', 'Rate Types Audit Log', 'Rates Audit Log', 'Routine Audit Log', 'Space Group Audit Log']],
  ['01-Configuration', ['ICD Portal Configuration', 'SAP Configuration', 'SAP TPI Configuration']],
  ['01-Investment', ['Investment Dashboard', 'Investment Requests']],
  ['Build', ['API Settings', 'Anomaly Methods', 'Collection Definition', 'Element Builder', 'Event Actions', 'Events', 'Function Composer', 'Routines', 'Source Types', 'Sources']],
];

const SPACE_ICONS = {
  'BAT Rates Integration': 'git-branch', 'Calendars Audit Log': 'calendar', 'Countries Audit Log': 'globe',
  'Currencies Audit Log': 'lock', 'Event Subscription Audit': 'credit-card', 'Rates Audit Log': 'lock',
  'Routine Audit Log': 'clock', 'Space Group Audit Log': 'square-dashed', 'ICD Portal Configuration': 'key',
  'API Settings': 'sliders-horizontal', 'Anomaly Methods': 'activity', 'Collection Definition': 'database',
  'Element Builder': 'layout-grid', 'Event Actions': 'circle-dot', 'Events': 'sun', 'Function Composer': 'function-square',
  'Routines': 'clock', 'Source Types': 'map-pin', 'Sources': 'map-pin',
};

function Sidebar({ open, current, onSelect }) {
  const [q, setQ] = React.useState('');
  if (!open) return null;
  return (
    <aside style={{ width: 300, flex: '0 0 300px', background: 'var(--op-surface)', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '20px 22px 12px', display: 'flex', alignItems: 'center', gap: 14 }}>
        <Icon name="menu" size={20} color="var(--op-text)" />
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 400, fontSize: 21, letterSpacing: '.16em', color: 'var(--op-text)' }}>onepilot</span>
      </div>
      <div style={{ padding: '10px 18px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'var(--op-input)', borderRadius: 999, padding: '12px 18px' }}>
          <Icon name="search" size={17} color="var(--op-text-muted)" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search spaces" style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--op-text)', fontFamily: 'var(--font-sans)', fontSize: 14.5 }} />
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 10px 10px' }}>
        {SPACE_GROUPS.map(([group, items]) => {
          const shown = items.filter((i) => i.toLowerCase().includes(q.toLowerCase()));
          if (!shown.length) return null;
          return (
            <div key={group} style={{ marginBottom: 18 }}>
              <div style={{ padding: '8px 12px', fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--op-text)' }}>{group}</div>
              {shown.map((item) => (
                <button key={item} onClick={() => onSelect(item)} style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 14, padding: '9px 12px',
                  background: current === item ? 'var(--op-input)' : 'transparent', border: 'none', borderRadius: 8,
                  cursor: 'pointer', textAlign: 'left', fontFamily: 'var(--font-sans)', fontSize: 14.5,
                  color: current === item ? 'var(--op-text)' : 'var(--op-text-muted)',
                }}>
                  <Icon name={SPACE_ICONS[item] || 'file-text'} size={16} color="var(--op-text-muted)" />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item}</span>
                </button>
              ))}
            </div>
          );
        })}
      </div>
      <div style={{ padding: '16px 22px 20px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 14.5, color: 'var(--op-text)' }}>Dirk Neumann</div>
        <div style={{ fontSize: 12.5, color: 'var(--op-text-muted)', marginTop: 3 }}>dirk.neumann@brisken.com</div>
        <AppButton variant="accent" icon="log-out" style={{ marginTop: 14, fontSize: 13.5, padding: '9px 16px' }}>Sign Out</AppButton>
        <div style={{ fontSize: 12, color: 'var(--op-text-muted)', marginTop: 12 }}>Release Notes</div>
      </div>
    </aside>
  );
}

function TopBar({ sidebarOpen, onToggleSidebar, title, search, onSearch, onAssistant }) {
  return (
    <header style={{ display: 'flex', alignItems: 'center', gap: 22, padding: '18px 28px' }}>
      {!sidebarOpen ? (
        <button onClick={onToggleSidebar} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--op-text)', padding: 0 }}>
          <Icon name="menu" size={20} color="var(--op-text)" />
        </button>
      ) : null}
      <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 400, fontSize: 26, color: 'var(--op-text)', margin: 0, whiteSpace: 'nowrap' }}>{title}</h1>
      {search ? (
        <div style={{ flex: 1, maxWidth: 700, display: 'flex', alignItems: 'center', gap: 14, background: 'var(--op-input)', borderRadius: 12, padding: '14px 20px' }}>
          <Icon name="search" size={18} color="var(--op-text-muted)" />
          <input placeholder="Search" onChange={(e) => onSearch && onSearch(e.target.value)} style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--op-text)', fontFamily: 'var(--font-sans)', fontSize: 15 }} />
        </div>
      ) : null}
      <button onClick={onAssistant} title="Assistant" style={{
        marginLeft: 'auto', width: 30, height: 30, borderRadius: 999, background: 'var(--op-mark)',
        border: 'none', cursor: 'pointer', flex: '0 0 auto',
      }} />
    </header>
  );
}

function AssistantPanel({ open, onClose }) {
  if (!open) return null;
  return (
    <aside style={{ width: 480, flex: '0 0 480px', borderLeft: '1px solid var(--op-border)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '18px 24px' }}>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--op-text-muted)', fontSize: 22 }}>&times;</button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div style={{ alignSelf: 'flex-end', background: 'var(--op-input)', borderRadius: 999, padding: '12px 20px', fontSize: 14.5, color: 'var(--op-text)' }}>
          anything you can say about this?
        </div>
        <div style={{ display: 'flex', gap: 14 }}>
          <span style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--op-mark)', flex: '0 0 auto' }} />
          <div>
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: 'var(--op-text)' }}>
              Nothing started in this window yet. The Integration Monitor is filtered to 2026-07-26 &ndash; 2026-07-27, so
              there is nothing to explain until a routine runs.
            </p>
            <AppButton variant="filled" icon="thumbs-up" style={{ marginTop: 14, fontSize: 13.5, padding: '9px 16px' }}>Pick up where we left off</AppButton>
          </div>
        </div>
      </div>
      <div style={{ margin: 24, background: 'var(--op-surface)', border: '1px solid var(--op-border)', borderRadius: 12, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
        <Icon name="paperclip" size={17} color="var(--op-text-muted)" />
        <Icon name="image" size={17} color="var(--op-text-muted)" />
        <input placeholder="" style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--op-text)', fontFamily: 'var(--font-sans)', fontSize: 15 }} />
        <Icon name="send" size={19} color="var(--op-accent)" />
      </div>
    </aside>
  );
}
