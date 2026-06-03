# No File Bloat (W1)

**Hard constraint.** Do NOT create files under `workspace/clients/*/`,
`workspace/projects/*/`, or other working-state folders unless the
file serves one of the allowed purposes in section 1. Default = do
not create. Update an existing file or surface the finding inline.

The cost of an unused file is not zero. It slows `/comd_resume`,
dilutes search and grep results, and creates ambiguity about which
docs are load-bearing for the current state. Two-week-old
inspection JSONs and one-off analysis scripts are the most common
offenders.

## 1. Allowed file purposes

Create a new file ONLY if one of these applies:

1. **Canonical state** (one per client / project; tracks live config,
   routing, persistent operational truth). Examples:
   `infrastructure.yaml`, `comms-log.md`, `pilot-routing.md`,
   `business-context.md`, `README.md`. Updating these is preferred
   over creating new ones.
2. **Active piece / spec / runbook** (one per discrete piece of work
   in flight). Examples: `piece1-status.md`,
   `piece2-apollo-filter-spec.md`, `piece3-mejixmas-setup-plan.md`.
   DELETE when the piece ships or is abandoned, not "superseded
   banner + leave in place".
3. **Re-usable reference data**. Audience CSVs / cohort lists that
   the build will load directly, weekly-report templates,
   test-fixture registries. Must be referenced by an active build
   step at write time.
4. **Active script**. Will run again (repeat builds, periodic
   audits, re-enrichments). NOT one-off investigations.
5. **Canonical client-authored content**. Copy the client themselves
   wrote (sequence cadence, voice samples). One canonical file per
   piece; delete superseded versions.

## 2. Disallowed (do not create)

- **API response dumps.** Don't save raw JSON output to disk unless
  the build will read it. Print the relevant fields to stdout,
  distill the finding into 1-2 sentences in an existing doc,
  discard the rest. If you find yourself writing
  `state-2026-MM-DD.json`, the live API IS the state; query it
  when needed.
- **Investigation snapshots.** Provenance checks, sequence pulls,
  state inspections; surface the finding in conversation. If the
  finding is important enough to persist, write 1-2 sentences in
  an existing doc (memory, pilot-routing, piece-status). Do NOT
  save the inspection JSON alongside.
- **Superseded plans / designs.** When a doc is superseded, DELETE
  it in the same change. Do not leave a "SUPERSEDED" banner;
  that's clutter that gets read on every search and adds cognitive
  load for no return. The superseding doc inherits prior work via
  prose mention if continuity matters.
- **One-off analysis scripts.** If a script will not run again,
  run it inline (`python -c`, heredoc) and discard the script.
  "Save it in case we need it later" almost always means "we
  won't and the saved version will be stale when we do".
- **Drafts of messages already sent.** Sent messages live verbatim
  in `comms-log.md` appendix; that is the canonical record.
  Pre-existing `drafts/<file>.md status: SENT` convention is
  being phased out. New sent-message drafts: log the verbatim
  text to `comms-log.md`, delete the draft file.

## 3. Pre-creation gate (mandatory, fires at decision time)

Before creating ANY file under `workspace/clients/*/` or
`workspace/projects/*/`, answer four questions in working context:

1. **Does an existing file already fit?** Search the target
   directory first. If yes: update that file, do not create.
2. **Who else will read this?** If "no one but me, once" → do not
   create.
3. **When will it be re-read?** If "never" → do not create.
4. **What decision / action does it enable?** If "none concrete"
   → do not create.

If all four pass cleanly, write the file. If any fail, surface
the finding inline instead.

## 4. Supersession discipline (all context data)

When new context data replaces old context data, DELETE the old in
the same change. This applies to **every** kind of context artifact,
not just plan docs:

- **Plan / design / spec docs** — when rewritten or replaced by a
  newer plan, delete the prior version.
- **Status / progress docs** — when a newer dated status doc
  supersedes an earlier one for the same piece of work, delete the
  earlier one.
- **JSON dumps / API response captures** — when a newer pull
  invalidates an older one (mailbox health, campaign state,
  inventory census, provenance audit), delete the older snapshot.
  The live API IS the state.
- **Audit / inspection results** — when a finding is re-verified
  in a current session and the verified finding lands in memory /
  pilot-routing / a piece-status doc, delete the original
  inspection artifact (script AND result).
- **Design drafts** — when a canonical version takes over (e.g.
  client returns their own copy and that becomes the canonical),
  delete the agent-side design drafts that preceded it.
- **Internal review artifacts** — round-1 / round-2 / round-N
  iterations of internal review docs: keep only the final
  version, delete the rounds.

Rules of supersession:

- DELETE in the same change that creates / locks the superseding
  artifact, not later "we'll clean up at checkpoint".
- Reference prior work via prose ("locked 2026-05-25 superseding
  the 2026-05-17 design") only if operational continuity actually
  matters. Most superseded docs don't need a continuity reference.
- Do NOT leave the old file with a `status: SUPERSEDED` banner.
  Banners get read on every search; the file is clutter regardless
  of the banner.
- Do NOT keep "for historical context" or "in case we need to
  refer back". Memory / friction-register / git history hold the
  historical record. Working folders hold current truth.
- This applies inside `drafts/` too: round-1 drafts of a cadence
  that round-2 replaces should be deleted, not kept as
  `status: SUPERSEDED`.

## 5. Periodic cleanup

The agent runs a context audit when:

- Asked by the user
- At `/comd_checkpoint` if `workspace/clients/{client}/context/`
  has grown by more than 10 files since the previous checkpoint
- After any session that ran 5+ investigations (each typically
  generates a script + a result file pair that should NOT survive)

The audit produces three buckets: DELETE (clear unused), KEEP
(active / canonical), YOUR CALL (borderline). The agent
auto-deletes the DELETE bucket; surfaces the YOUR CALL bucket
to the user as a decision point.

## 6. Why

User audit 2026-06-01 of `workspace/clients/meji-media/context/`
found, over a ~3 week build period:

- 36 unsent message drafts in `drafts/` (deleted same day under
  separate "stop drafting without ask" correction; see
  [[feedback_no_unrequested_client_drafts]])
- 9 point-in-time JSON snapshots from finished investigations
- 10 one-off analysis scripts that had run once and would not
  run again
- 3 superseded plan docs that had never been deleted because
  "SUPERSEDED" banners were added instead

The bloat hurt three concrete things:

1. `/comd_resume` loads slower and includes content irrelevant
   to the current state.
2. Memory / friction-register recall pulls stale findings
   alongside current ones.
3. It becomes ambiguous which docs are load-bearing for the
   current state, which is exactly the problem
   `pilot-routing.md` was built to solve at a smaller scale.

Root cause: every investigation produced both the script AND
the result file AND any intermediate analysis. By default.
Without asking. This rule moves the default the other way:
print findings, save canonical state, delete the rest.

Operationalises at Layer 1 (structural gate, fires at decision
time) rather than Layer 3 (memory, depends on agent recall),
because the failure pattern was systematic and recurrent across
both the meji-media and the wimmer build periods, not a one-off.

Related: [[feedback_no_unrequested_client_drafts]] (sister rule
on outbound comms drafting), [[rule_behaviors]] B2 (mark-done
gate that catches the "did I delete the superseded file" check).
