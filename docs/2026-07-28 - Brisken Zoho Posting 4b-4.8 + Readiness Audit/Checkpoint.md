# Checkpoint: Brisken Zoho Posting 4b-4.8 + Readiness Audit

**Date:** 2026-07-28
**Status:** Shipped (PR #465 merged, Fly v50) + live audit complete

---

## Summary

Built the direct Zoho Books journal-posting path (4b) with the 4.8
idempotency ledger per owner order: connection exists, ships completely
OFF, and a ledger cross-reference before upload makes duplicate imports
structurally impossible. Then audited the deployed receipt-first tool
end to end for Criss-readiness: every technical surface passes; the
three remaining gaps are human actions.

---

## What Was Done This Session

### Zoho posting (4b) + idempotency ledger (4.8)
1. `zoho/client.py`: `create_journal` + `list_journals` (write path
   reachable only via the gated CLI; 4xx-vs-ambiguous error split).
2. `zoho/idempotent.py`: `PostLedger` sqlite (runlog conventions;
   refs/hashes/journal-ids, never amounts), write-ahead intent
   (`inflight` commits before any POST), content-hash conflict
   detection, ambiguous-failure quarantine + batch abort, confirm-only
   verify with grace-window clearing, cross-org duplicate refusal,
   COA-verdict blockers on hand-edited CSVs.
3. `zoho_post_cli.py`: `expense-recon zoho-post` posts the REVIEWED
   export CSV by Reference# (send-by-id), dry-run default; `--go` needs
   config `zoho.post.enabled` (strict boolean) AND
   `EXPENSE_RECON_ZOHO_POST=1` AND the narrow-only org allowlist
   (822741658/697686691 hardcoded) AND a clean plan; `--expect N`
   count assert; journals post as `draft`.
4. Adversarial review before ship: 26-agent find→refute workflow
   confirmed 16 defects (verify-clears-inside-the-race-window,
   silent 0-row ledger updates, cross-org double-post,
   config-replaceable allowlist, truthiness kill switch, DO-NOT-USE
   smuggling, unpinned column contract). All 16 fixed + test-pinned
   same session. Suite 901 → 954 green.
5. Shipped: PR #465 merged on green CI (6 checks), Fly v50 deployed
   from the clean deploy worktree, healthz 200 + API-only gate
   verified. Change is inert on Fly (no creds, env unset, no web
   surface).

### Live Criss-readiness audit (deployed origins, real path)
1. Unauth probes (5-agent fan-out): healthz 200; `/` + `/login` JSON
   401 no-HTML; CORS preflight exact-echoes the SPA origin; SPA serves
   a real TanStack shell whose bundle points at exactly one API origin
   (the right one).
2. Authed e2e on the live app: login with the operator code → created
   a `UTIL - readiness probe` expense batch with a generated receipt
   image → vision read it exactly (CAFE ROMA, 4.50 EUR, Espresso;
   Cornetto) → categorized to `CorpServ | Travel Expense | Food` →
   Zoho Expenses CSV in the full import shape → batch deleted,
   deletion verified (404), Criss's 3 real runs untouched.
3. Browser-path probe (agent-browser, named session): SPA URL →
   operator code → dashboard renders the month-lifecycle UI (Months /
   Start a new month / Classic reconciliation / EN-PT). The exact
   path Criss would take works.

---

## Key Decisions Made

### Post the reviewed CSV artifact, not a rebuild
- **Choice:** `zoho-post` consumes the export CSV grouped by
  Reference#, resolved against the entity chart.
- **Rationale:** what posts is byte-for-byte what a human reviewed
  (send-by-id discipline, `rule_brisken_graph_send_by_id`); the reader
  lives beside the writer so the column contract cannot drift.

### Absence is never proof of non-commit
- **Choice:** verify is confirm-only by default; clearing needs
  `--clear-absent` AND the row aged past `grace_hours` (1h default).
- **Rationale:** the exact failure class that creates ambiguous rows
  (timeout/5xx) can commit server-side after any point-in-time
  listing, and draft journals may not appear in the unfiltered list.
  The review caught this as its top finding.

### Ledger marks are UPSERTs
- **Choice:** `mark_posted`/`mark_ambiguous` restore a concurrently
  deleted row instead of silently updating 0 rows.
- **Rationale:** preserves "no journal in Zoho without a ledger
  record" under every interleaving of `--forget`/`--verify` with an
  in-flight POST.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `...expense-reconciliation/src/expense_recon/zoho/client.py` | edit | 4b write path + `_post` + `list_journals` |
| `...src/expense_recon/zoho/idempotent.py` | new | 4.8 ledger + plan/execute/verify |
| `...src/expense_recon/zoho_post_cli.py` | new | gated `zoho-post` CLI |
| `...src/expense_recon/output/zoho_export.py` | edit | `read_journal_csv` (true line numbers) |
| `...src/expense_recon/cli.py` | edit | `zoho-post` argv-peek dispatch |
| `...tests/test_zoho_{idempotent,post_cli,client}.py` | new/edit | 53 new tests |
| `...BLUEPRINT.md`, `...ANNEALING.md` | edit | 4.7/4.8 rows + resolved-2026-07-28 entry |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | 4.8/4b element row (built, OFF) |

All merged via PR #465.

---

## Current Status

p1 expense-recon: backend live at Fly **v50** (healthz 200, API-only
gate intact); receipt-first mode ON and verified end-to-end on the
deployed origin today; Zoho posting path built but OFF behind four
gates. brisken platform: unknown plan (`infrastructure.yaml` has no
platform section for this FastAPI stack — expected). Comms-log: none
tracked for p1.

Audit verdict: the tool is technically ready for Criss. The blockers
are human:
1. **She has never been sent the SPA URL** — her one emailed link
   (`brisken-expense-recon.fly.dev`) dead-ends at bare JSON 401 with
   zero pointer (evidence-confirmed incl. browser-UA requests).
2. **Settings entities registry is empty** — exports carry
   `(paid-through - assign)` until a default paid-through account is
   configured.
3. **`EXPENSE_COLUMNS` unvalidated** against the tenant's real Zoho
   Expenses import template (owner, Zoho scope).

---

## Next Steps

1. Dirk sends Criss `brisken-reconcile-dash.lovable.app` + operator
   code (the single gap between the tool and a user; owner action).
2. Populate the settings `entities` registry (default_paid_through for
   Corporate Services) so receipt-first exports import clean.
3. Owner: validate `EXPENSE_COLUMNS` vs the real Zoho Expenses import;
   Books journal-write scope re-consent stays the gate for ever
   turning `zoho.post` on (plus per-action go, B5-class).
4. Optional structural fix for the wrong-link trap: serve a minimal
   HTML pointer to the SPA for browser hits on the API origin.
5. p2 status files stale 37d (`p2-lead-gen-general`, `p2-outreach`) —
   refresh from a p2-scoped session, not this p1 session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md`
  (resolved-2026-07-28 entry = the full 4.8 design + review record)

### Open Questions
- Backend-origin browser hits: add an HTML pointer page to the SPA, or
  rely solely on re-sending the correct link? (owner call)

### Working Notes
- Zoho v3 journals API has NO idempotency and `status: draft|published`
  on create (verified from docs 2026-07-28); the unfiltered journals
  list is not documented to include drafts — that assumption is why
  verify never auto-clears.
- `learning_cli._zoho_config_from_env` is the creds derivation that
  matches the real `.env` (ZOHO_BOOKS_REFRESH_TOKEN wins, ZOHO_DC=com
  alias); `ZohoConfig.from_env` alone would mis-derive the DC.
- Playwright MCP here expects the user's Edge CDP on :9222 (was down);
  agent-browser with a named session worked for the SPA probe.
- Fly deploy from `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-deploy`
  (detached at origin/main) — the pattern held cleanly.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/465
- Zoho journals API: https://www.zoho.com/books/api/v3/journals/

---

## How to Continue

`/comd_resume brisken` → the p1 status file + ANNEALING entry carry the
whole state. Nothing in the posting path may be enabled without an
explicit owner order; next real movement is the Criss handoff (owner)
or the entities-registry fill (agent-doable on request).

---

## Strategic Feedback

### What Worked Well This Session
- Enumerate-before-build (B7) fired at design time and killed a wrong
  build: classic 4.8 guarded a posting surface that did not exist; the
  reframe surfaced a real owner decision instead of dead code.
- The adversarial review workflow earned its cost: 16 confirmed
  defects pre-ship, two of them genuine duplicate-window races in the
  exact property the module exists to guarantee.

### Suggestions
- The `(paid-through - assign)` placeholder will appear in every
  receipt-first export until the entities registry is filled; a
  5-minute settings write (owner-confirmed account) removes the last
  cosmetic "unfinished" signal Criss would see.

### System Health
- Autonomy: 2 human interventions (1 clarification after an
  over-compressed explanation of the 4.8 fork; 1 genuine owner
  decision at that fork). Gates: B1:1 B2:6 B3:1 skipped:0 (the B1
  stop-gate caught a closing-offer deferral and it was executed
  in-session; the gate held, the residual is the authoring habit).
- Register at 404 KB — archive split ships in this checkpoint's docs
  PR.
