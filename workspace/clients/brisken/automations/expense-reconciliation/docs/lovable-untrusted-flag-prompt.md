# Lovable prompt: show what a flagged receipt said, in the reviewer's language (item 93)

**Background.** Since PR #973 the backend flags a receipt whose document, file
name or carrying mail contains text written at the tool rather than about a
purchase ("ignore previous instructions", "mark this as matched"). The tool
never acts on that text; it puts the row in "Needs a look" with
`review.reason_code: "untrusted_instructions"` and sends the offending excerpts
in `expenses[].untrusted_instructions` as `[{kind, quote}]`. The SPA has no copy
for the code, so the row shows the backend's English sentence, which names the
kinds as machine slugs, and the quotes themselves are never shown: the reviewer
is told to read something without being shown what. This prompt adds the copy
in English and Portuguese and renders the quotes as plain text. No backend or
API change.

## Paste this into Lovable

1. In `src/lib/api.ts`, on the expense row type (the one that carries
   `review`, `boxes` and `duplicate`), add:

   ```ts
   /** Agent-directed text found in this receipt, its file name or its mail.
    *  Reported, never obeyed. `quote` is untrusted text: render as TEXT only. */
   untrusted_instructions?: { kind: string; quote: string }[];
   ```

2. In `src/lib/i18n.tsx`, next to the other `expx.review.reason.*` keys, add in
   both languages:

   English:
   - `"expx.review.reason.untrusted_instructions": "This receipt contains text addressed to the tool, not about the purchase. Nothing was done because of it. Read the excerpt below and check the receipt is genuine before confirming."`
   - `"expx.untrusted.kind.ignore-previous-instructions": "tells the tool to ignore its instructions"`
   - `"expx.untrusted.kind.addresses-the-assistant": "speaks to the tool as an assistant"`
   - `"expx.untrusted.kind.instructs-a-status-change": "asks for a status (matched, approved, private...)"`
   - `"expx.untrusted.kind.instructs-a-send-or-forward": "asks for something to be sent or forwarded"`
   - `"expx.untrusted.kind.instructs-a-fetch": "asks the tool to fetch a web address"`
   - `"expx.untrusted.kind.instructs-a-rule-change": "asks for a rule or setting to change"`

   Portuguese:
   - `"expx.review.reason.untrusted_instructions": "Este recibo contém um texto dirigido à ferramenta, e não à compra. Nada foi feito por causa dele. Leia o trecho abaixo e confira se o recibo é legítimo antes de confirmar."`
   - `"expx.untrusted.kind.ignore-previous-instructions": "manda a ferramenta ignorar as instruções"`
   - `"expx.untrusted.kind.addresses-the-assistant": "fala com a ferramenta como se fosse um assistente"`
   - `"expx.untrusted.kind.instructs-a-status-change": "pede um status (conciliado, aprovado, privado...)"`
   - `"expx.untrusted.kind.instructs-a-send-or-forward": "pede que algo seja enviado ou encaminhado"`
   - `"expx.untrusted.kind.instructs-a-fetch": "pede que a ferramenta acesse um endereço da web"`
   - `"expx.untrusted.kind.instructs-a-rule-change": "pede a mudança de uma regra ou configuração"`

3. In `src/components/ExpensesReviewGrid.tsx`, in the expense row, directly
   under the existing review-reason line (the `{reason ? (<div className="mt-0.5
   px-1 text-[11px] italic text-muted-foreground">{reason}</div>) : null}`
   block), render one line per entry of `row.untrusted_instructions` when the
   list is non-empty:

   - the localized kind (`t("expx.untrusted.kind." + kind)`; if the key is
     missing, show the raw `kind`), then a colon, then the `quote` in quotation
     marks, same small muted style as the reason, not italic;
   - render `quote` as a plain React text child ONLY. Never
     `dangerouslySetInnerHTML`, never inside an `<a>`, never passed to a
     markdown renderer, never auto-linked, even when it looks like a URL or an
     email address. It is text from a stranger;
   - `break-words` so a long excerpt wraps inside the cell.

   The reason line itself needs no code change: `reviewReason()` already
   resolves `review.reason_code` through `reasonKey()`, so with the key present
   the row shows the new copy.

**Do not change:** the review-reason lookup, any other i18n key, the grid's
grouping or filters, any API call, auth (bearer token), or the Confirm controls.

## Verify after publish

Bundle audit: `chunk-i18n` carries `expx.review.reason.untrusted_instructions`
and `expx.untrusted.kind.instructs-a-status-change` in both languages; the grid
chunk reads `untrusted_instructions`. No live row carries a flag (0 of 135
expense rows across the six months, read 2026-09-17 evening; every row already
carries the key), so the render is verified on the next flagged receipt or with
a TEST- drop that is deleted in the same session.
