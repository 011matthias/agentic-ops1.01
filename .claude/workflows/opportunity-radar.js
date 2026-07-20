export const meta = {
  name: 'opportunity-radar',
  description: 'Client opportunity deep sweep: deterministic feeds, lens fan-out, cross-checks, scored ranked brief, adversarial verification',
  whenToUse: 'Invoked by /comd_radar {client} deep. Requires the client to have a weekly-review blueprint with a sec-J lens catalog, an opportunity-radar.md ledger, and an analysis engine with a --radar mode. Read-only against live systems; never drafts client outbound.',
  phases: [
    { title: 'Feeds', detail: 'engine --radar + lens-catalog extraction' },
    { title: 'Lenses', detail: 'one read-only agent per catalog lens' },
    { title: 'Cross-checks', detail: 'named integrity checks against live state' },
    { title: 'Synthesize', detail: 'dedup vs ledger, score per sec J2, rank' },
    { title: 'Verify', detail: 'adversarial re-pull of the brief\'s claims' },
    { title: 'Record', detail: 'corrected brief + ledger update + status bump' },
  ],
}

// args: { client: 'meji-media', date: 'YYYY-MM-DD', agents?: 12 }
// date comes from the invoker because Date.now() is unavailable in workflow scripts.
// Some invocation paths deliver args as a JSON string; normalize before reading.
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const client = A.client
const runDate = A.date
if (!client || !runDate) throw new Error(`args {client, date} required (got: ${JSON.stringify(args).slice(0, 200)})`)
const maxLenses = A.agents || 12

const ROOT = `workspace/clients/${client}/context`
const RO = 'HARD CONSTRAINT (B5): read-only against every live system. GET and read-style POST list endpoints only. Never POST/PUT/PATCH/DELETE mutations, never send or schedule email, never modify campaigns, leads, scenarios, data stores, or DNS. If a check would need a mutation, report it as a gated candidate instead of performing it.'

phase('Feeds')
const CATALOG_SCHEMA = {
  type: 'object', required: ['lenses', 'crosschecks', 'rubric'],
  properties: {
    lenses: { type: 'array', items: { type: 'object', required: ['num', 'name', 'feed'], properties: { num: { type: 'number' }, name: { type: 'string' }, feed: { type: 'string' }, cadence: { type: 'string' } } } },
    crosschecks: { type: 'array', items: { type: 'string' } },
    rubric: { type: 'string' },
  },
}
const [catalog, feeds] = await parallel([
  () => agent(`Read ${ROOT}/weekly-review-blueprint.md section J. Return: the J1 lens catalog (num, name, feed, cadence per lens), the named cross-checks listed at the end of J1, and the full J2 scoring rubric text verbatim.`, { label: 'catalog', phase: 'Feeds', schema: CATALOG_SCHEMA }),
  () => agent(`${RO}\nRun the client's analysis engine in radar mode: find the engine named in ${ROOT}/weekly-review-blueprint.md frontmatter 'related:' (an analysis-scripts/*.py), run it with --radar (python, from its own directory; it self-throttles and takes minutes), and return the full console output verbatim including the RADAR machine-pass section. On failure return the error output.`, { label: 'engine', phase: 'Feeds' }),
])
if (!catalog) throw new Error('lens catalog extraction failed')

phase('Lenses')
const FINDINGS_SCHEMA = {
  type: 'object', required: ['findings'],
  properties: { findings: { type: 'array', items: { type: 'object', required: ['lens', 'claim', 'evidence'], properties: { lens: { type: 'string' }, claim: { type: 'string' }, evidence: { type: 'string' }, N: { type: ['number', 'null'] }, gate: { type: ['string', 'null'], enum: ['autonomous', 'owner', 'client', null] } } } } },
}
const lensResults = await parallel(catalog.lenses.slice(0, maxLenses).map(l => () =>
  agent(`${RO}\nClient: ${client}. You are the "${l.name}" lens of the opportunity radar. Feed: ${l.feed}. Ground yourself in ${ROOT}/ (comms-log.md frontmatter + recent entries, risk-register.md, pilot-routing.md, opportunity-radar.md, weekly-reviews/) and the live read-only sources the feed names. Engine radar output for context:\n${String(feeds || '').slice(0, 6000)}\nReturn leaks, gaps, or ROI opportunities this lens surfaces that are NOT already rows in ${ROOT}/opportunity-radar.md. Each finding: one-line claim, concrete evidence with its source, N (affected units, sourced; null if unknown), gate class. Label speculation as speculation.`, { label: `lens:${l.name.slice(0, 24)}`, phase: 'Lenses', schema: FINDINGS_SCHEMA })
))

phase('Cross-checks')
const CHECK_SCHEMA = { type: 'object', required: ['check', 'verdict', 'detail'], properties: { check: { type: 'string' }, verdict: { type: 'string', enum: ['pass', 'fail', 'unknown'] }, detail: { type: 'string' } } }
const checkResults = await parallel((catalog.crosschecks || []).map(c => () =>
  agent(`${RO}\nClient: ${client}. Run this integrity cross-check against LIVE state (read-only), grounding in ${ROOT}/: "${c}". Return pass/fail/unknown with concrete evidence; unknown = no read path exists, name what would be needed.`, { label: `check:${c.slice(0, 28)}`, phase: 'Cross-checks', schema: CHECK_SCHEMA })
))

phase('Synthesize')
// Barrier is deliberate: scoring and dedup need every lens + check result together.
const found = lensResults.filter(Boolean).flatMap(r => r.findings)
const BRIEF_SCHEMA = { type: 'object', required: ['brief', 'claims'], properties: { brief: { type: 'string' }, claims: { type: 'array', items: { type: 'string' } } } }
const synth = await agent(`Client: ${client}. Synthesize the deep-sweep brief.\nScoring rubric (apply exactly; scores are internal-only):\n${catalog.rubric}\nLens findings (JSON):\n${JSON.stringify(found).slice(0, 24000)}\nCross-check results (JSON):\n${JSON.stringify(checkResults.filter(Boolean)).slice(0, 8000)}\nDedup against the existing ledger ${ROOT}/opportunity-radar.md. Score every surviving finding (N sourced or TBD->watch). Produce: (1) 'brief' = ranked markdown (scored table; top-3 work-now; gated items in one owner-decision block; rejects with one-line reasons); (2) 'claims' = the discrete factual claims the brief depends on, aim for 15+.`, { label: 'synthesize', phase: 'Synthesize', schema: BRIEF_SCHEMA })
if (!synth) throw new Error('synthesis failed')

phase('Verify')
const VERDICT_SCHEMA = { type: 'object', required: ['claim', 'verdict', 'correction'], properties: { claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'overstated'] }, correction: { type: 'string' } } }
const audits = await parallel((synth.claims || []).slice(0, 20).map(cl => () =>
  agent(`${RO}\nClient: ${client}. Adversarially verify against LIVE data (fresh read-only pull; do not trust cached docs): "${cl}". Default to overstated when the evidence is thinner than the claim. Return confirmed/refuted/overstated plus the correction if any.`, { label: `verify:${cl.slice(0, 28)}`, phase: 'Verify', schema: VERDICT_SCHEMA })
))
const corrections = audits.filter(Boolean).filter(a => a.verdict !== 'confirmed')
log(`verify: ${audits.filter(Boolean).length} claims re-pulled, ${corrections.length} correction(s)`)

phase('Record')
const rec = await agent(`Client: ${client}. Run date: ${runDate}. Finalize the deep sweep.\nDraft brief:\n${synth.brief.slice(0, 24000)}\nVerification corrections (apply ALL first; drop refuted claims, soften overstated ones):\n${JSON.stringify(corrections).slice(0, 8000)}\nThen: (1) write the corrected brief to ${ROOT}/weekly-reviews/${runDate}-deep-sweep.md, deleting any older *-deep-sweep.md there (supersession); (2) update ${ROOT}/opportunity-radar.md - add/refresh candidate rows with next RAD-NN ids, prune promoted/rejected rows per the ledger's own rules, set last_deep_sweep to ${runDate}; (3) bump 'updated:' in workspace/clients/${client}/status/ops-radar.md if present. Do NOT commit; do NOT draft anything client-facing. Return one paragraph: candidates added, corrections applied, top-3 work-now.`, { label: 'record', phase: 'Record' })

return { summary: rec, findings: found.length, claimsAudited: audits.filter(Boolean).length, corrections: corrections.length }
