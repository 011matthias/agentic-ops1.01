# Test fixtures for agnt_proposal-research

Persistent fixtures for re-running the proposal-research agent's smoke tests across sessions. Re-runnable; never deleted.

## Files

- **posting-track2.txt** — realistic Track 2 job posting (named company "Atlas Greenhouses GmbH", named contact, ~$1,500 budget, clear must-haves and nice-to-haves, EU/GDPR angle, explicit deliverable expectations). Expected output: SUCCESS shape with all `research:` fields populated, requirement coverage matrix listing all 5 must-haves + 3 nice-to-haves + 1 anti-requirement, cherry-pick reasoning with at least 3 entries (Track 2 threshold). Test invocation should pass `prospect_name="Atlas Greenhouses GmbH"`, `job_posting={absolute path to posting-track2.txt}`, `track_hint="2"`.

- **posting-blocked-empty.txt** — single-line posting ("Need automation help.") — under the 50-word threshold. Expected output: BLOCKED shape with `[posting-empty]` blocker. Test invocation should pass `prospect_name="Vague Prospect"`, `job_posting={absolute path to posting-blocked-empty.txt}`. (The agent should fetch / read the file, detect it's < 50 words, and return BLOCKED.)

## How to re-run

1. Open a session in this repo.
2. Invoke the agent via the Task tool with `subagent_type: agnt_proposal-research` (or, while the agent isn't picked up by the runtime registry mid-session of its creation, role-play via the `general-purpose` agent with the agnt_proposal-research.md content as the prompt — same workaround used in Phase 1/2/3/4).
3. Pass `prospect_name` + `job_posting` (and optionally `track_hint`) per the fixture's "Test invocation should pass" line.
4. Compare the agent's output against the expected shape:
   - **posting-track2.txt → SUCCESS shape:** all 11 `research:` fields populated (some may be `""` or `[]` if genuinely absent, but most should have content); requirement coverage lists all must-haves and nice-to-haves; cherry-pick reasoning section has ≥3 tuples with `claim` / `source_line` / `why_this_prospect` each; Coverage notes either says "full coverage" or surfaces real gaps; `Sources consulted:` line names at minimum the job posting and profile-copy.md.
   - **posting-blocked-empty.txt → BLOCKED shape:** `## Research BLOCKED — Vague Prospect`, single `[HIGH] [posting-empty]` finding, footer line "What's needed to unblock: ..."

## What "PASS" means for the fixtures

- **posting-track2.txt PASS:** SUCCESS shape, no preamble, all required sections present, no invented field values (every `job_language_echoes` entry verbatim-traceable to the posting; every `prospect_systems` entry actually named in the posting), each cherry-pick has explicit `why_this_prospect` reasoning. Track depth: 2, gates: passed (or "partial" with specific Coverage note).
- **posting-blocked-empty.txt PASS:** exactly the BLOCKED shape with `[posting-empty]` (or `[invocation]` if inputs were genuinely malformed). No SUCCESS-shape leakage.

## What "FAIL" means

- posting-track2.txt FAIL modes:
  - Preamble before the `##` header
  - Fabricated values not traceable to the posting (e.g., inventing "Sebastian has 15 years of experience" when only "Operations Lead" is in the posting)
  - Cherry-picks without `why_this_prospect` reasoning
  - Missing the `Sources consulted:` or `Track depth:` lines
  - Lifting verbatim copy from an existing proposal as a "cherry-pick" (cross-contamination is a hard rule violation)
  - Closing offers ("happy to also research X if useful")
- posting-blocked-empty.txt FAIL modes:
  - SUCCESS shape with fabricated content ("Vague Prospect appears to be in the SaaS industry...")
  - Wrong blocker tag (e.g., `[invocation]` when the input was structurally valid but textually empty)
  - Missing "What's needed to unblock" footer

## Notes

- The Track 2 fixture deliberately includes both standard must-haves and a "What we don't want" section to exercise the requirement coverage matrix's handling of anti-requirements (treat as a constraint that should map to a deliverable's framing — e.g., the cover letter must NOT propose a rebuild-from-scratch).
- The fixture's "GREENHOUSE" code-word requirement is a real Upwork pattern — the requirement coverage matrix should list it explicitly so the cover letter writer doesn't drop it.
- The agent does external research where possible (Dimension C). For this fixture, the company name "Atlas Greenhouses GmbH" is synthetic — WebFetch results will be empty / irrelevant; the agent should note this in Coverage notes rather than fabricate company details.
- If `agnt_proposal-research` evolves, update the fixture's "Test invocation should pass" line and re-document the expected shape changes here.

## Runnable via the eval harness

The BLOCKED fixture is re-runnable via `uv run tools/eval-agents.py run --fixture research-blocked` (WebFetch deliberately not allowlisted); grading contract pinned in `tools/tests/test_agnt_evals.py`.
