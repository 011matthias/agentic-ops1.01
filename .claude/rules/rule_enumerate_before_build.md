# Enumerate-Before-Build Gate (B7)

**Hard constraint.** Before proposing NEW infrastructure, or designing
an integration around an EXTERNAL capability, enumerate what already
exists and what the surface actually is — by querying it live, not by
inferring from memory, a docs page, or an inputs schema. Build or
propose only after the enumeration.

This is a decision-time boundary in the B-gate family (B1–B4 in
[[rule_behaviors]], B5 in [[rule_instantly_invasive]], B6 in
[[rule_no_auto_commit]]). It consolidates two recall-dependent memories
([[feedback_enumerate_existing_infrastructure]],
[[feedback_verify_limitations_before_asserting]]) into one Layer-1 gate,
because both failed by recall across May–June 2026: the knowledge
existed as memory and the agent built past it anyway.

## Two enumeration triggers

The gate fires at two distinct decision points.

**E1 — Existing client infrastructure (before proposing new).** Before
recommending a new domain, account, mailbox, pipeline, data store, or
any infra that serves a purpose the client may already have
provisioned: enumerate ALL existing infra serving that purpose, querying
live state per piece (Instantly `/api/v2/accounts`, DNS, the
orchestrator's connection list, the client's existing
scenarios/workflows, `context/` + `infrastructure.yaml`). A single dead
or partial piece does NOT generalize to "they have nothing" — check each
piece on its own. (2026-05-25: recommended a new cold-sending domain
before querying Instantly, which already held three warmed domains on
Porkbun + Google Workspace; the query would have ended a four-revision
iteration at iteration zero.)

**E2 — External tool / connector / action surface (before building
around it).** Before designing a flow that depends on a third-party
connector, MCP server, GitHub Action, or API: enumerate its ACTUAL
capability surface and runtime prerequisites — the available operations
(does the primitive you need actually exist?), the auth model, the
free-tier / quota constraints, and the setup prerequisites that live in
the setup README, not in the inputs schema. Never assume a primitive
exists because the integration "should" have it. (2026-05-20: built an
entire email-delivery flow around the claude.ai Gmail connector, which
exposes only drafts / labels / read and has no send primitive. 2026-05-20:
Resend's free tier only delivers to the account-owner address.
2026-06-06: `claude-code-action` needs `id-token: write` plus the GitHub
App installed on the repo — neither is listed in `action.yml` inputs,
both live in the setup doc.)

## Protocol

At either trigger, before the first build / propose step:

1. Name the surface to enumerate (the client's existing X; the
   connector's operation list; the action's prerequisites).
2. Query it live: an MCP list/get call, an API GET, a `gh` / CLI call,
   a WebFetch of the setup doc, or a read of the client's
   `infrastructure.yaml` / `context/`. One concrete query path per
   piece.
3. If there is NO query path, write "UNVERIFIED — no enumeration path
   for {surface}" and treat the capability as ABSENT until proven, never
   present-by-assumption. (Mirrors B4's "TBD > fabricated number"; an
   unverified capability claim — "the connector can send", "they have no
   domain yet" — is a deferral-shaped assertion per
   [[feedback_verify_limitations_before_asserting]].)
4. Build or propose only against the enumerated reality.

## Why

Both halves recurred 5+ times across May–June 2026, and each was already
a memory that failed by recall before it became this gate:

- E1 traces to [[feedback_enumerate_existing_infrastructure]] (2026-05-25
  twice, plus the meji warm-rebuild infra confusion). The memory was
  loaded; the agent proposed new infra anyway and iterated four times
  before the existing infra was queried.
- E2 traces to the 2026-05-20 verification-theater cluster (Gmail
  no-send, Resend free-tier recipient rule, GitHub source-gate) and the
  2026-06-06 `claude-code-action` prerequisite miss, plus
  [[feedback_verify_limitations_before_asserting]]. "Works via the
  integration I imagined" is the same class as "compiles ≠ works": the
  integration's real surface was never read before the build depended on
  it.

Per the self-annealing ladder ([[rule_behaviors]] Layer 1: tool >
structural gate > memory), a behavioral decision-boundary that is not
cleanly pattern-matchable by a hook belongs at the rule layer (fires at
decision time, always loaded), not at the memory layer (depends on
recall) where it twice did not hold.

## Enforcement

Agent discipline at decision time (B7). Before the first build / propose
action of any session that introduces new infra or a new external
integration, run the E1 / E2 enumeration and state what was found.

Backstops already in this space: B4's `unsourced-claim` gate
(`validate-output.py`, via `post-write-gate.py`) catches an unsourced
capability CLAIM once it reaches a deliverable; the autonomous-first
diagnostics rule in [[rule_behaviors]] already mandates querying
fixtures / tools / MCP before asking the user. This gate moves the check
EARLIER — to design time, before the proposal or the build, rather than
after the claim has reached a deliverable.

**Self-detection.** Proposing new infra without enumerating the existing
estate, or building around an external capability without reading its
real surface, is an `agent-deferred` / `missed-tool` /
`verification-theater` friction event — log at `/comd_checkpoint`. The
recurrence-kill is this gate firing at design time, not memorizing
harder.

Related: [[rule_behaviors]] (B1–B4, autonomous-first diagnostics),
[[rule_instantly_invasive]] (B5), [[rule_no_auto_commit]] (B6),
[[feedback_enumerate_existing_infrastructure]],
[[feedback_verify_limitations_before_asserting]].
