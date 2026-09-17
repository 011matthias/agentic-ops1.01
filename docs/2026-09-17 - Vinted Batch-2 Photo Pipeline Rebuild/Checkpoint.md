# Checkpoint: Vinted Batch-2 Photo Pipeline Rebuild

**Date:** 2026-09-17
**Status:** Shipped. All three batch-2 listings live with rebuilt photos, verified by downloaded pixels.

---

## Summary

The three published batch-2 jeans listings (Levi's 32, Diesel 33, Tommy 34) had
their photos rebuilt through seven stages over six rounds of owner feedback:
capture correction, neutral background, tone walk-back, shade match to the
owner's reference set, background on the close-ups, and finally background
smoothing. The owner's stated reference, the GAS "tiger" jeans, turned out never
to have been edited at all; what makes those photos good is that they were shot
on a light surface.

---

## What Was Done This Session

### Photo pipeline (`.scratch/vinted/`, seven stages)

1. `enhance_photos.py` — crop to garment at 3:4, per-item white balance from the
   floor, midtone gamma metered on the garment, mild unsharp. Replaced an
   initial multiplicative gain after measurement showed the garment's p98 was
   already at 234, so scaling drove up to 4.9% of frame to pure white.
2. `neutral_bg.py` — oak floor replaced with a light neutral on the full
   flat-lays. Restricted to flat-lays because the first draft bleached the
   Levi's and Hilfiger leather patches.
3. `deepen.py` — denim walked back to as-shot, undoing the 43-50% midtone lift
   stage 1 had applied to items 32 and 34.
4. `shade_match.py` — matched to the GAS reference's luminance (40), one
   exposure per item. Hue held at each shot's own value.
5. `neutral_bg_all.py` — background on the close-ups too, with declared
   protection for the two leather patches and a colour rule for the tapes.
6. `smooth_bg.py` — background luminance field blurred at 60px so knots, plank
   seams and grain stop reading as smudges.
7. `driver/replace_photos.py` — swaps photos on a live listing without it ever
   being empty: upload first, confirm old+new in the grid, then delete index 0
   exactly `old` times, then Save.

### Verification tooling (`.scratch/vinted/driver/`)

- `verify_photos_live.py` — scoped to `item-photo-N--img` and `item-price`, with
  a built-in control that the three listings must return distinct photo sets.
- `verify_live_pixels.py` — downloads what Vinted serves and measures garment
  luminance against every pipeline stage.
- `verify_live_bg.py`, `verify_live_smooth.py` — same, for oak fraction and for
  background texture.

### Research

- Five-agent workflow (`wf_11e00a16-0d5`) established the GAS tiger jeans were
  never enhanced: 131 transcripts, the filesystem, the repo and git history all
  came back empty, and no session was even running when the files were written.

---

## Key Decisions Made

### The reference's darkness is exposure, not cloth

- **Choice:** Match the GAS full-length shots' luminance (40) rather than treat
  "the GAS shade" as one number.
- **Rationale:** Within that folder the same trousers photograph at 32, 47, 98
  and 114. The dark look comes from the camera stopping down against a white
  background. A reference that contradicts itself 3.5x has no single shade.

### One exposure per item, not one target per shot type

- **Choice:** Derive the gamma once per item from its full-length shots, then
  apply it across that item's whole set.
- **Rationale:** Matching each shot to its own kind of reference shot put item
  33's full-length photos at luminance 39 beside its own close-ups at 85. A
  buyer swiping through sees the same trousers at two shades.

### Declared regions for two leather patches

- **Choice:** Hard-code protection rectangles for the Levi's and Hilfiger
  patches; everything else spatial or colour-based.
- **Rationale:** Colour is identical (246,204,151 patch vs 239,189,133 floor),
  six warmth/brightness rules all left the patch connected to the frame corner,
  and morphology cannot help. For two shapes in two photographs, declaring beats
  a threshold fitted to four samples.

### Proceeded on the colour change after raising the concern once

- **Choice:** Darkened the denim on the owner's instruction, anchored first to
  as-shot and then to the reference.
- **Rationale:** Their standing rule is no recolouring, because photos are the
  evidence for condition claims. They hold the garment and I do not. Concern
  stated once, they reaffirmed, so it is their call; the anchor keeps it
  defensible rather than arbitrary.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.scratch/vinted/enhance_photos.py` | rewritten | capture correction, gamma tone |
| `.scratch/vinted/neutral_bg.py` | created | neutral background, flat-lays |
| `.scratch/vinted/neutral_bg_all.py` | created | neutral background, all shots |
| `.scratch/vinted/deepen.py` | created | walk the midtone lift back to as-shot |
| `.scratch/vinted/shade_match.py` | created | match the GAS reference luminance |
| `.scratch/vinted/smooth_bg.py` | created | flatten background grain and knots |
| `.scratch/vinted/driver/replace_photos.py` | created | swap photos on a live listing |
| `.scratch/vinted/driver/verify_*.py` | created (4) | verify by content, not by id |
| `memory/reference_vinted_photo_look_target.md` | created + extended | the look target, the pipeline table, the traps |
| `memory/reference_vinted_sell_form.md` | extended | edit-form photo swap, two counting traps |

---

## Current Status

All three listings live and verified against downloaded pixels: 4 / 5 / 6
photos, prices EUR 25 / 32 / 22, titles and descriptions untouched, no
duplicates. Garment luminance 38-49 against the reference's 40. Oak fraction
0.0-0.2% on full-length shots; 6.4-9.7% on close-ups, of which untreated floor
is 0.0% on five of seven and 1.4% on the two with measuring tapes, the rest
being leather patches and tan stitching that must stay. Background small-scale
variation 0.4-0.9 (was 5-7).

Ops status: vinted-reselling has no `infrastructure.yaml` and no comms-log; it
is an owner-operated project, not a client automation.

---

## Next Steps

1. Shoot batch 3 on a white sheet or roll of paper. Every stage after capture
   correction exists only to undo an oak floor; on a light surface none of it
   runs.
2. Item 31 (Weekday shirt) is still unpublished for want of a size.
3. The 12 absent batch-1 listings: sold or pulled is still unresolved, and it
   decides whether 33 favourites across 16 listings reads as working or
   stalling. The owner's Vinted app answers it.
4. Batch-1 description problems remain unfixed: item 28's undisclosed 4-5 mm
   mark, item 18's "weiss" measuring light blue plus a contradicted "Pique",
   item 29's "schwarz" measuring RGB 30,49,77.
5. Rework keyword lines for the 6 still-open batch-1 items (18, 19, 21, 26, 29,
   30), all on the critic's do-not-apply list.

---

## Context for Next Session

### Files to Read First

- `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/memory/reference_vinted_photo_look_target.md`
- `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/memory/reference_vinted_sell_form.md`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\vinted\neutral_bg_all.py` (the docstring carries the measurements)

### Open Questions

- Does the owner want the same treatment applied to the 16 open batch-1
  listings? They are all on the same oak floor.
- The GAS files are Pillow-q92, EXIF-stripped and band-limited, so something
  re-encoded them, and nothing attributes that to any actor. Unexplained, not a
  lead. Resolving it means diffing against the phone's camera roll.

### Working Notes

**What cannot be separated by colour.** Tan leather and tan oak: Levi's patch
246,204,151 against floor 239,189,133; Hilfiger 219,182,146 against 194,146,99.
Six warmth and brightness rules were tested for connectivity and every one left
the patch in the same component as the frame corner, because a patch sits at a
waistband's top edge with floor directly above.

**What can.** The measuring tape: R-G is -2 to -6 (yellow, red and green equal)
against oak's +41. The G-B half of the test keeps denim out, since denim's G-B
is negative. Garment vs oak floor: blue-minus-red, validated across all 16 shots
(flat-lays 57-63% warm, close-ups 13-31%).

**Masks break when the background changes.** Blue-minus-red stopped working once
the background was neutralised, because neutral grey has b-r near zero and reads
as denim; the audit came back claiming the live garment sat at luminance 208.
After neutralising, separate on saturation instead, and exclude warm.

**A per-channel curve is not hue-neutral.** Darkening by LUT crushed red hardest
and pushed the denim to B/R 4.04 against a reference of 2.58. Scale all three
channels by one shared per-pixel factor instead.

**Failed approaches.** Colour-distance-from-border mask (inverts after cropping,
because the cropped border is garment). Red mask overlay (unreadable on tan).
Three sample windows aimed by intuition that all landed on something other than
the target. A 55px keep-out band to protect patches (leaves exactly the brown
rim the owner objected to).

### Reference Materials

- Listings: `vinted.de/items/10019997776`, `/10020006363`, `/10020014572`
- Reference set: `C:\Users\neuma_p1qrsic\iCloudDrive\Personal\Vinted-GAS-Jeans`
- Stage folders: `iCloudDrive\Vinted\<n> - ...\upload` through `upload7`
- Comparison sheets: `.scratch\vinted\before-after\`

---

## How to Continue

The originals and all seven stages sit side by side on disk, so reverting is
pointing `replace_photos.py --from=<folder>` at an earlier stage and re-running.
Verify with `driver/verify_live_smooth.py`, which reads the live bytes rather
than photo ids. Chrome must be running with `--remote-debugging-port=9222` and
`--user-data-dir=C:\Users\neuma_p1qrsic\.vinted-automation-profile`.

---

## Strategic Feedback

### What Worked Well This Session

- Every instrument was validated against a known case before its output was
  trusted, and this caught four separate broken probes: a page-wide scraper that
  returned identical photos for three different listings and still printed a
  pass; a mask that inverted after cropping; a pairing bug that reported four
  false failures; and a replacement run that silently did nothing while photo
  ids still changed.
- Refusing to tune a threshold once the measurement showed no threshold exists.
  Tan leather and tan oak were sampled, found identical, and the approach
  switched to spatial rather than continuing to fit constants.

### Suggestions

- Render a labelled coordinate grid before sampling any region of an image.
  Three sample windows were aimed by intuition this session and all three
  missed, twice producing confident numbers about the wrong object. The grid
  resolved it in one pass.

### System Health

- Autonomy: 11 human interventions, 6 of them corrections to the same artifact
  (elevated; run `/system-dev` to close gaps). The reference set was in hand
  from round two, and each round I measured only the dimension the owner had
  just named rather than diffing every dimension against their reference at
  once. That pattern, not any single defect, is what made this six rounds.
