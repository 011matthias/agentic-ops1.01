# Lovable prompt: say WHICH line still needs a category (item 160)

**Background.** On July's page the owner pointed at a row and wrote "this
should not be mentioned here i think...". The row was Microsoft Corporation
718.20. Its category column showed a settled category, `Software &
Subscriptions`, and directly under it the sentence "One or more receipt lines
still need a category before this can post." Both are true: the category on
the row is the roll-up of the lines that DO have one, and that receipt's
second line (25.20, "(illegible)") has none. Read beside a filled category
field, a sentence that names nothing reads as a mistake. The backend now sends
which lines it means, as `expenses[].uncategorized_lines`; this prompt makes
the screen say it. No backend or API change.

## Paste this into Lovable

1. In `src/lib/api.ts`, on the expense row type (the one that carries
   `review`, `line_items`, `books_as` and `posting_category`), add:

   ```ts
   /** The receipt lines that carry no category yet — the exact lines the
    *  `partial_uncategorized` / `uncategorized` review reason is about.
    *  `index` indexes `line_items`. Absent when every line has a category. */
   uncategorized_lines?: { index: number; description: string; line_total: string }[];
   ```

   Example payload, from the owner's July row:

   ```json
   "uncategorized_lines": [
     { "index": 1, "description": "(illegible)", "line_total": "25.20" }
   ]
   ```

2. In `src/lib/i18n.tsx`, next to the other `expx.*` keys, add in both
   languages. `{count}`, `{total}` and `{amount}` are interpolated:

   English:
   - `"expx.uncategorized.one": "1 of {total} receipt lines still needs a category: {amount}."`
   - `"expx.uncategorized.many": "{count} of {total} receipt lines still need a category."`
   - `"expx.uncategorized.line": "Needs a category"`
   - `"expx.uncategorized.hint": "The category shown on the row covers the other lines. This one has to be set before the expense can post."`

   Portuguese (pt-BR):
   - `"expx.uncategorized.one": "1 de {total} linhas do recibo ainda precisa de categoria: {amount}."`
   - `"expx.uncategorized.many": "{count} de {total} linhas do recibo ainda precisam de categoria."`
   - `"expx.uncategorized.line": "Falta categoria"`
   - `"expx.uncategorized.hint": "A categoria mostrada na linha cobre as outras. Esta precisa ser definida antes que a despesa possa ser lançada."`

3. In `src/components/ExpensesReviewGrid.tsx`, in the CATEGORY column (the one
   that renders `posting_category` and, under it, the review reason):

   - when `row.review.reason_code === "partial_uncategorized"` AND
     `row.uncategorized_lines` is a non-empty array, do NOT render the generic
     `expx.review.reason.partial_uncategorized` sentence. Render instead:
     - `expx.uncategorized.one` when the array has exactly one entry, with
       `{total}` = `row.line_items.length` and `{amount}` = that entry's
       `line_total` formatted the way the grid formats every other amount
       (same currency as the row);
     - `expx.uncategorized.many` otherwise, with `{count}` = the array length
       and `{total}` = `row.line_items.length`;
   - keep it in the same muted review-reason style and the same position it
     occupies today, so nothing moves on screen; only the words change;
   - put `expx.uncategorized.hint` on it as a `title`, so hovering explains
     why a row showing a category is still asking for one.

   Leave `reason_code === "uncategorized"` exactly as it is today. That row
   shows no category at all, so its sentence contradicts nothing and needs no
   rewrite.

4. In the per-line block (the one that already lists `line_items` with their
   own categories for a split receipt), mark each line whose `index` appears
   in `row.uncategorized_lines` with the short `expx.uncategorized.line` label
   where that line's category would otherwise read. Use the same warning
   colour the grid already uses for a row that needs attention; do not add an
   icon, a badge count or a new control. This is the placement half of the
   fix: the sentence in the category column says how many, the line block
   says which.

5. Nothing keys on the new field beyond those two renders: no new filter, no
   new sort, no change to any box count, no change to the Confirm or Keep
   controls, and no new request. Setting the category on the line through the
   control that already exists makes the field disappear on the next refetch,
   because the backend builds it from the same predicate the verdict reads.

**Do not change:** the `posting_category` value or its source line, the
`books_as` split rendering, the `uncategorized` reason copy, any other
`expx.review.reason.*` string, the grid's grouping, filters or box counts,
any API call, or auth (bearer token, `API_BASE`
`https://api.expenses.brisken.com`).

## Verify after publish

1. Open July, find Microsoft Corporation 718.20. The category column reads
   `Software & Subscriptions` and, under it, "1 of 2 receipt lines still needs
   a category: 25.20." The old "One or more receipt lines..." sentence is
   gone from that row.
2. Expand that row's line block: line 2 ("(illegible)", 25.20) carries "Needs
   a category"; line 1 keeps its own category.
3. Switch the language to Portuguese and read both again.
4. A row with no category at all still reads the `uncategorized` sentence,
   unchanged.
5. Set the category on that line with the existing control; both the sentence
   and the line label go away on the refetch.
