# Lovable prompt: make the way into a month visible

Paste into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). No backend change; nothing to deploy
on our side. This touches the `/months` screen only.

## Why

The operator left this on `/months` on 2026-08-28, anchored on a row's
Created cell:

> why cant the user enter and view or edit the month

Nothing is broken. Every month opens: the API serves all six on both routes,
and `lovable-months-list-prompt.md` built the links. The problem is that the
way in is invisible.

Measured on the published build (`chunk-months-Bvb2xrOV.js`, fetched
2026-08-28):

- The month name is the only clickable thing in the row. It carries
  `className="underline-offset-2 hover:underline"`, so at rest it is
  styled exactly like the plain text in every other cell. It announces
  itself as a link only once the pointer is already on it.
- The table row has no click handler. The counts, the Statement badge and
  the Created date are inert, which is where the operator clicked.
- The per-row menu holds exactly two items, Rename and Delete. Someone
  hunting for the way in opens it, finds no Open, and concludes the month
  cannot be entered.

Three small changes fix it. Keep everything else on the screen as it is.

## 1. The month name reads as a link at rest

Give the name the app's link treatment without hovering: `text-primary` plus
`underline` (keep `underline-offset-2`), or whatever the app already uses
for a text link elsewhere. Reuse the existing token; do not invent a colour.

Keep both destinations exactly as they are: `has_statement: true` goes to
`/runs/{run_id}`, `false` goes to `/expenses/{batch_id}`.

## 2. The whole row opens the month

Clicking anywhere in the row opens the same destination as the name.

- The actions cell is excluded. Stop propagation there so the menu button,
  the menu items, and the Rename and Delete dialogs never navigate.
- `cursor-pointer` on the row, plus the app's existing row hover
  background, so the row looks clickable before it is clicked.
- Keep the name as the focusable link. The row click is a convenience on
  top of it, not a replacement: tab order and Enter must still work, and a
  middle click or Ctrl+click on the name must still open a new tab.

## 3. Open, as the first item in the row menu

Above Rename, with a separator between Open and the destructive pair if the
menu has one elsewhere.

Copy: EN "Open" / PT "Abrir".

Same destination as the name. This is the item the operator went looking
for.

## 4. The actions button says what it is

The trigger currently carries `aria-label={label}`, so an icon-only button
announces itself as "April 2026", the same name as the link two cells to
its left.

Make it EN "Actions for April 2026" / PT "Acoes de April 2026", built from
the row's label.

## Do not

- Do not change the columns, the counts, the Statement badge, or the
  create form.
- Do not touch the batch page, the workbench, Email intake or Settings.
- Do not add a second primary button to the row. The row itself plus the
  menu item is the whole fix.
- Do not make the Created cell a separate link.
- No em-dashes in UI copy.

## Verify after publish

On `/months`, the month names are visibly links before hovering. Clicking a
row's Created cell opens that month. The row menu reads Open, Rename,
Delete, and Open lands on the batch page for a month without a statement and
on the workbench for one with a statement. Rename and Delete still open
their dialogs without navigating.
