# Lovable prompt: show the note the sender typed above the forward (item 155)

**Background.** When Dirk forwards a vendor invoice to the intake mailbox he
types the filing instruction above it: "BTS only", "CorpServ only / Dev IT
costs", "This is ZOHO BOOKS for CorpServ / So it is split between BCS and BTS /
Booked to It subscriptions in CorpServ.", sometimes a card ending. That text
exists nowhere in the attached PDF, and it is the entity, the cost split and the
category, stated by the person who knows. The backend read it and dropped it;
since this change it carries it onto every receipt that mail delivered and sends
it as `expenses[].operator_note`. 30 of the 92 stored mails carry one. The SPA
has no renderer for it, so today the reviewer still cannot see it. This prompt
adds the render. No backend or API change.

**It is display only.** The text comes from an e-mail, so it decides nothing:
the backend does not read an entity, a category, a cost center, a card or a
recipient out of it, and neither should the screen. Do not parse it, do not
match it against the entity or category lists, do not prefill any control from
it, do not use it to sort or filter. It is shown to the reviewer, who decides.

## Paste this into Lovable

1. In `src/lib/api.ts`, on the expense row type (the one that carries `review`,
   `boxes`, `submitted_by` and `untrusted_instructions`), add:

   ```ts
   /** What the sender typed ABOVE the forward, as they typed it: the filing
    *  instruction ("BTS only", "CorpServ only / Dev IT costs"). May contain
    *  newlines. Absent when the mail carried no note of its own.
    *  Untrusted text from an e-mail: render as TEXT, act on nothing. */
   operator_note?: string;
   ```

   It also rides inside `submitted_by` (`submitted_by.operator_note`). Read the
   ROW key; the provenance copy is the same string and needs no type change.

2. In `src/lib/i18n.tsx`, next to the other `expx.*` keys, add in both
   languages:

   English:
   - `"expx.operator_note.label": "Note from the sender"`
   - `"expx.operator_note.hint": "Typed above the forwarded e-mail. Nothing was decided from it."`

   Portuguese:
   - `"expx.operator_note.label": "Observação de quem enviou"`
   - `"expx.operator_note.hint": "Escrita acima do e-mail encaminhado. Nada foi decidido a partir dela."`

3. In `src/components/ExpensesReviewGrid.tsx`, in the expense row, render the
   note when `row.operator_note` is a non-empty string. Put it directly UNDER
   the existing `submitted_by` chip ("From: <address>"), because it answers the
   same question the chip opens, and ABOVE the review-reason line:

   - a small quoted block: the localized label in the muted style used by the
     chip, then the note itself in normal (not italic) text, indented with a
     left border the way a blockquote reads;
   - preserve the sender's line breaks (`whitespace-pre-line`) and wrap long
     lines (`break-words`). A note is one to three short lines in practice and
     at most 40 lines by contract;
   - the localized hint as a `title` on the block, so hovering says why the
     screen is showing it and that nothing was decided from it;
   - render `row.operator_note` as a plain React text child ONLY. Never
     `dangerouslySetInnerHTML`, never inside an `<a>`, never through a markdown
     renderer, never auto-linked, even when it contains something that looks
     like a URL or an address. It is text from an e-mail.

4. Nothing else keys on it: no new filter, no new sort, no badge in the box
   counts, no change to any Confirm control. A row with a note is an ordinary
   row that shows one more line.

**Do not change:** the `submitted_by` chip itself, the review-reason line, the
`untrusted_instructions` lines under it (item 93), the grid's grouping, filters
or box counts, any API call, or auth (bearer token, `API_BASE`
`https://api.expenses.brisken.com`).

## Verify after publish

Bundle audit: the grid chunk names `operator_note`, and `chunk-i18n` carries
`expx.operator_note.label` in both languages. On live data, open August 2026 and
look at the rows whose mail carried an instruction: the Lovable rows read
"CorpServ only / Dev IT costs" and "BTS only", the Zoho Books row reads the
three-line split. A row whose mail carried no note shows nothing new, and an
uploaded receipt (no `submitted_by`) shows nothing new either.
