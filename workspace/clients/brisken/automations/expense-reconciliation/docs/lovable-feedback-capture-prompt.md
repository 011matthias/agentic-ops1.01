# Lovable prompt — double-click feedback capture on EVERY page

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`.

An earlier version of this widget already exists in the app (it produced real
notes on the home page, run pages, and the memory page). This prompt makes it
**global**: mounted once at the app root so it works on every current and
future page, triggered by **double-click**, capturing the exact click
location. If the old per-page version still exists, replace it with this one
global mount; do not run both.

---

## Behavior

**Mount once in the root layout** (inside the authenticated shell), so every
route has it: dashboard, run review, expense batches, merchants editor,
settings, memory, compare, help — and any page added later. The only screen
without it is the login screen (there is no token yet).

1. **Trigger: double-click anywhere on the page.**
   - Ignore double-clicks inside text inputs, textareas, selects, and
     contenteditable elements (double-click there means "select a word").
   - Ignore double-clicks while the feedback popover is already open.
   - Do not preventDefault on the page's own double-click behaviors beyond
     opening the popover.
2. **On trigger, capture the location silently** (before the user types):
   - the clicked element's CSS selector path (id or tag + nth-of-type chain)
   - the clicked element's visible text, trimmed to 300 chars (`anchor`)
   - the nearest section heading above the click — closest h1/h2/section
     title text (`section`)
   - coordinates: `pageX`, `pageY`, `clientX`, `clientY`, `scrollY`,
     viewport `vw`/`vh`, document height `docH`, and `pct` = percent down
     the page (integers)
3. **Show a small popover at the click point:** a textarea, a Send button and
   a Cancel button. Labels: **EN** "Leave feedback about this spot" / **PT**
   "Deixar um comentário sobre este ponto"; Send = "Send" / "Enviar";
   Cancel = "Cancel" / "Cancelar". Esc or clicking outside closes it.
   Keep it compact and unobtrusive; it must never cover the full screen.
4. **On Send, POST to `/api/feedback`** with the bearer token:

```json
{
  "comment": "<the typed text — required, do not send empty>",
  "path": "<current route, e.g. /batches/13b5605012f9>",
  "title": "<document.title>",
  "section": "<nearest heading text>",
  "anchor": "<clicked element text, ≤300 chars>",
  "selector": "<CSS selector path>",
  "run_id": "<the run/batch id when the current view shows one, else omit>",
  "pos": { "pageX": 0, "pageY": 0, "clientX": 0, "clientY": 0,
           "scrollY": 0, "vw": 0, "vh": 0, "docH": 0, "pct": 0 }
}
```

   - `run_id` matters: on a run page OR an expense-batch page, send that
     run/batch id explicitly (the backend accepts it as of today). This is
     what lets a note say "on THIS month's batch" no matter what the route
     is called.
   - All `pos` values are integers. Send the fields you have; the backend
     drops unknown ones.
5. **After a 200**, close the popover and show a brief toast: **EN**
   "Feedback sent — thank you" / **PT** "Comentário enviado — obrigado".
   On failure, keep the popover open with the text intact and show
   "Could not send — try again" / "Não foi possível enviar — tente novamente".

## Discoverability

Add one subtle, persistent hint so the function is findable without being
noisy: a small muted line in the footer or the help menu — **EN**
"Double-click anywhere to leave feedback on that spot" / **PT** "Clique duas
vezes em qualquer lugar para deixar um comentário sobre aquele ponto". No
floating buttons, no pulsing badges.

## Out of scope

- No screenshots, no session recording — the location fields above are the
  whole capture.
- Do not build a feedback-viewing UI; notes are read on the backend
  (`/feedback.jsonl`). If a "Feedback" nav item already exists, leave it as
  it is.
