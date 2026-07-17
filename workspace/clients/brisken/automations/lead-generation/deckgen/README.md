# Brisken deck-foundation-v2 (clone-and-patch deck build)

Builds Brisken product-deck **proposals** on the design foundation of Dirk's
own `OnePilot Solutions Overview 2026.pptx` (owner directive 2026-07-17: take
that deck as the foundation, rebuild the assets, replace low-quality builds).
Every output is native Dirk-brand PowerPoint: his masters, layouts, theme,
media and embedded fonts (Poppins / Open Sans / Lato), because composition
never draws a shape from scratch — it clones and patches slides of a library
derived from his file.

Replaces the pptxgenjs "dark-cockpit" pipeline in `.scratch/deckgen/` for
product decks, and resolves the wipe-risk debt: all build code here is
tracked; the only binaries live in gitignored context and are re-fetchable.

## Flow

```
uv run fetch-reference.py            # SP -> context/decks/reference-2026/   (CDP :9223)
uv run make-library.py               # reference -> library.pptx + manifest
uv run compose.py <deck>             # specs/<deck>.yaml -> dist pptx + banned-terms gate
uv run render.py <deck>              # PowerPoint COM -> PDF + QA PNGs + structural checks
CDP_PORT=9223 uv run upload.py <deck>|--all   # -> SharePoint 2026_PPTX/Asset Testing ONLY
```

Decks: `mdh-commodities`, `market-data-hub`, `smart-trading`,
`digital-co-worker`, `overview-revision`.

## Homes

- Engine: `tools/pptx_slide_ops.py` (+ pytest in `tools/tests/`, CI runs it
  with `--with python-pptx`).
- Binaries (gitignored, re-fetchable): `workspace/clients/brisken/context/
  decks/reference-2026/` — the pristine reference + derived `library.pptx`.
  Scripts resolve this against the MAIN clone (first `git worktree list`
  entry), so builds work from feature worktrees too.
- Outputs (ephemeral): `.scratch/deckgen-v2/dist/<deck>/` and `qa/<deck>/`
  in the main clone. The deliverable of record is the Asset Testing copy.

## The library

`make-library.py` copies the reference, renames patchable shapes to semantic
roles (`library-manifest.json` is the committed pattern/role map), and
authors three patterns the reference lacks: `short-version`, `problem`
(shell; body is deck-unique), `platform-context` (the OnePilot hierarchy
slide; compose highlights one app box). **Reference-drift tripwire:** if
Dirk restructures his deck, a rename stops matching and make-library fails
loudly naming the slide/shape — update `RENAMES` against the new structure.

Specs speak the directive language documented in `compose.py` (set / paras /
outline / runs / sub / image / from_shape / highlight / smartart). `runs`
patches fail hard when a donor text stopped matching — same tripwire.

## Guards

- `compose.py` and `render.py` both run `tools/validate-demo-material.py
  --client brisken` (banned content: Evonik, RWZ, BTP). Hidden slides,
  dangling rIds and missing embedded fonts fail the build.
- `upload.py` can write to exactly one folder: `2026_PPTX/Asset Testing`.
  No other destination is expressible in that script.
- Uploads are proposals named `... 2026-08 PROPOSAL.pptx`; they can never
  collide with Dirk's live files.

## BTP decision log

Default: architecture slides say "on SAP's own cloud" (Dirk's own
validator-clean phrasing) instead of "SAP Business Technology Platform"
(banned by his standing "Exclude BTP from all demos" directive). His
reference deck DOES print the BTP name on architecture chips and ships the
official "SAP Certified: Built on SAP Business Technology Platform" badge
image (images are invisible to the validator; the badge stays because it is
his certification mark). Both facts are flagged in every proposal report;
if Dirk opts in per deck, restore the text and add a scoped exemption to
`tools/fixtures/demo-banned-terms.json` citing his sign-off.

## Swap runbook (per deck, ONLY after Dirk's explicit approval — invasive)

1. `MoveToUsingPath` Dirk's live pptx+pdf from `Brisken Product Assets/`
   (or the Overview from the folder root) to `Archive/` — no-overwrite.
2. Rename the approved proposal (drop ` PROPOSAL`, adopt Dirk's naming) and
   move it from `Asset Testing/` to the live folder.
3. Re-pull the repo mirror (`deliverables/lead-generation/rome-2026/decks/`),
   update that README's page table, log the swap in `comms-log.md`.

## Known v1 simplifications

- The `problem` pattern is text-only (eyebrow/headline/bands-as-lines); the
  old decks' three-band diagram art is not reproduced. Iterate after Dirk's
  proposal review if he wants diagram art there.
- Smart Trading / Digital Co-Worker product-logo images on use-case
  one-pagers reuse whatever the spec could repoint (`from_shape`); decks
  without a clean product-logo shape keep the donor logo (flagged OPEN in
  the proposal report).
- SmartArt success slides are patched in place, never duplicated.
