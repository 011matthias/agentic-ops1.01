# Lovable prompt: the sender's note now classifies (item 250)

**Background.** Since item 155 the expense row shows the note the sender typed
above a forwarded receipt ("BTS only", "CorpServ only / IT costs") with the
hint "Nothing was decided from it." The owner ruled on 2026-10-07 that a note
from one of OUR senders (a Brisken address or one listed in Settings > Email
intake) now classifies the receipt: the company it names is applied, over the
paying card, and an account it names clearly is applied too. A stranger's note
still decides nothing. The backend says which on every row; the screen has two
new values to name and one sentence that is no longer true. Copy only: no new
control, no new call.

## Paste this into Lovable

1. In `src/lib/api.ts`, wherever the expense row's `entity_source` and
   `posting_category.source` are typed as string unions, add `"sender_note"`
   to `entity_source` and `"note"` to `posting_category.source`. If they are
   plain `string`, change nothing.

2. In `src/lib/i18n.tsx`, REPLACE the text of `expx.operator_note.hint` in both
   languages (the old text says nothing was decided, which is now wrong for
   our own senders):

   English:
   - `"expx.operator_note.hint": "Typed above the forwarded e-mail. When it comes from one of our own senders, the company it names, and an account it names clearly, are applied to this row. Change either as usual."`

   Portuguese:
   - `"expx.operator_note.hint": "Escrita acima do e-mail encaminhado. Quando vem de alguém da nossa equipe, a empresa que ela indica, e uma conta que ela indica com clareza, são aplicadas a esta linha. Altere qualquer uma como de costume."`

   And ADD, next to the other `expx.review.badge.*` keys:

   English:
   - `"expx.review.badge.short.note": "Note"`
   - `"expx.review.badge.note": "The account the sender named in the note above the forwarded e-mail."`
   - `"expx.entity.source.sender_note": "from the sender's note"`

   Portuguese:
   - `"expx.review.badge.short.note": "Observação"`
   - `"expx.review.badge.note": "A conta que quem enviou indicou na observação acima do e-mail encaminhado."`
   - `"expx.entity.source.sender_note": "pela observação de quem enviou"`

3. Company sub-label. Where the expense row renders the muted sub-label under
   the company from `entity_source` ("edited" / "from card" / "batch default"
   / "learned"), add the case `"sender_note"` rendering
   `t("expx.entity.source.sender_note")`. If that mapping already reads its
   text from i18n keys under another prefix, add the new key under that prefix
   instead and keep the same English and Portuguese text.

4. Category badge. `SourceBadge` already looks up
   `expx.review.badge.short.${source}` and `expx.review.badge.${source}` for
   each `"; "`-separated part of `posting_category.source`. Make sure `"note"`
   gets the SAME tone as `"learned"` (a decided answer that is not the
   reviewer's own pick), not the needs-review tone and not the `edited` tone.
   The "Undo my category" item stays keyed on `"override"` only: a note's
   account is not the reviewer's pick, and picking another account in the
   dropdown already replaces it.

Do not parse the note text, match it against any list, or prefill anything
from it on the screen. The backend has already applied what it decides; the
screen only names where the value came from.

## How to check

On a month with a mailed receipt whose sender wrote "BTS only" above the
forward, the row's company reads Consulting with "from the sender's note"
under it, in both languages, and hovering the note block shows the new hint.
No literal `expx.` key text appears anywhere.
