# Module: DATA

Load at **Build Procedure step 2**. Detail behind Definition-of-Done items 2 and 20
in `SKILL.md`. This is the B4 gate (`rule_behaviors.md`) applied to a built page.

## B4-safe data (`app/src/sites/{slug}/data.ts`)

Every field traces to `prospects/{slug}/data.md`. Sourced facts verbatim. Anything
unverified -> the `CHECK = "[BITTE PRÜFEN]"` sentinel in `data.ts`.

**Never invent** a price, menu item, email, phone, team, or zone. Categories are
often sourced even when items are not — list the sourced layer, flag the rest.

The rule: a flag beats a fabricated value. A page that ships flagging three
unverified fields is honest and correctable; a page that ships with three
plausible-but-invented prices is a B4 violation that reads as fact.

## The sentinel is data-layer only; the page renders it quietly (item 20)

`CHECK` is the source of truth in `data.ts`. It must NOT reach a pitchable page as
the raw, ALL-CAPS, bracketed `[BITTE PRÜFEN]` string: to a non-technical owner that
reads as a broken or unfinished form field (a List A5 authenticity tell). The visible
render is one of:

- a quiet muted "auf Anfrage" / "wird ergänzt" in normal body type (no loud chip), or
- an omitted row/field entirely (gate the markup on `value !== CHECK`).

Either way `data.ts` keeps `CHECK` unchanged, so the honesty and correctability are
preserved while the page stays pitchable. (Operationalized across the five sites
2026-06-03; see incidents.md.) The advisory `tools/audit-local-web-aesthetics.py`
greps the built HTML for any raw sentinel that leaked through.
