# Lovable prompt: show the colour a statement row is marked with (item 162)

**Background.** Criss marks her card workbook with cell fill, and the backend
read two families of it: yellow meant "already entered in Zoho" and gray meant
"a subscription". Every other shade was invisible to it, so a row she had
marked with something else looked exactly like a row she had marked with
nothing. On the live July workbook that was 84 of 112 rows.

Since this change the backend NAMES every fill it can read and sends them on
the charge row as `rows[].fills`. It still infers meaning from exactly two of
them; the rest are recorded and nothing is concluded from them. Owner
directive, 2026-09-20: *"dont attribute colors in the statements or receipts
any deeper meaning, all i need you to be able to do, is get the classifier to
read all these colors and more."* The screen's job is the same: show the
reviewer what the sheet is marked with, and claim nothing about what it means.
No backend or API change in this prompt.

**It is display only.** Do not map a colour to a status, a category, an
entity, a card or a filter. Do not infer that orange means "review", that blue
means "transfer" or that green means "done". Do not sort or group by it, do
not add a box count for it, do not prefill any control from it, and do not
change any existing chip. A colour the tool does not act on is shown, and the
reviewer decides whether it means anything.

## Paste this into Lovable

1. In `src/lib/api.ts`, on the charge row type (the one carrying
   `entry_status`, `effective_bucket` and `candidates`), add:

   ```ts
   /** One coloured cell on the statement row this charge was read from. */
   export type CellFill = {
     /** The column's header text. "" when the column has no header. */
     column: string;
     /** 0-based column index. The identity when a header repeats
      *  (the live workbooks carry two "Memo" columns). */
     index: number;
     /** The fill as read: six uppercase hex digits, no "#". The exact
      *  truth; `family` is only a coarse grouping of it. */
     hex: string;
     /** white | gray | black | red | orange | yellow | olive | green |
      *  cyan | blue | purple | pink */
     family: string;
   };
   ```

   and on the row:

   ```ts
   /** Every coloured cell on the source workbook row, left to right.
    *  ABSENT (not null, not []) when the row has no readable fill, and
    *  absent on every month read before this shipped: a statement is
    *  parsed at upload, so the colours appear when a month is next read.
    *  A RECORD of what the sheet is marked with. `entry_status` stays the
    *  only thing a colour decides. */
   fills?: CellFill[];
   ```

   Guard it like every other list: `Array.isArray(row.fills) ? row.fills : []`,
   and skip any element that is not an object with a string `hex`.

2. In `src/lib/i18n.tsx`, next to the other workbench row keys, add in both
   languages:

   English:
   - `"row.fills.label": "Marked in the sheet"`
   - `"row.fills.hint": "The colours this row carries in the workbook. Only yellow (already in Zoho) and gray (subscription) mean anything to the tool; the rest are shown as they are."`
   - `"row.fills.cell": "{column}: {family} ({hex})"`
   - `"row.fills.noColumn": "column {index}"`

   Portuguese (PT-BR):
   - `"row.fills.label": "Marcado na planilha"`
   - `"row.fills.hint": "As cores que esta linha tem na planilha. Só o amarelo (já no Zoho) e o cinza (assinatura) significam algo para a ferramenta; o resto é mostrado como está."`
   - `"row.fills.cell": "{column}: {family} ({hex})"`
   - `"row.fills.noColumn": "coluna {index}"`

   Add a family-name lookup in both languages, used for the `{family}`
   placeholder. English is the identity (`yellow` to "yellow"); Portuguese:
   `white` branco, `gray` cinza, `black` preto, `red` vermelho, `orange`
   laranja, `yellow` amarelo, `olive` verde-oliva, `green` verde, `cyan`
   ciano, `blue` azul, `purple` roxo, `pink` rosa. A family the lookup does
   not know falls back to the raw string, so a family added later still
   renders.

3. In the charge row of `src/components/MatchingWorkbench.tsx`, render the
   fills when the guarded array is non-empty. Put the strip on the row's
   detail area, next to the existing `entry_status` chip, since it answers the
   same question that chip opens:

   - one small swatch per fill, in the order given: a 10x10 rounded square
     whose `backgroundColor` is `#` + the `hex`, with a 1px border in the
     theme's muted colour so a white or near-white fill is still visible
     against the card;
   - the localized `row.fills.cell` string as the swatch's `title` and its
     `aria-label`, with `{column}` falling back to `row.fills.noColumn` when
     `column` is `""`. Colour alone is never the only carrier of the
     information;
   - the localized `row.fills.label` as a muted caption before the swatches,
     and `row.fills.hint` as the caption's `title`;
   - build the colour ONLY as `backgroundColor: "#" + hex` after checking
     `/^[0-9A-Fa-f]{6}$/`. Never interpolate `hex` into a class name, a
     `style` string, or any HTML.

4. Do NOT tint the row, the card or any cell with the fill colour. The swatch
   strip is the whole render. Tinting a row would re-attach a meaning to the
   colour, which is the thing the owner asked not to do, and it would collide
   with the bucket colours the workbench already uses.

5. Nothing else keys on it: no filter, no sort, no box count, no badge, no
   change to the `entry_status` chip, the Confirm control, the candidate list,
   or the grouping.

**Do not change:** the `entry_status` chip and its two labels, bucket colours
or grouping, any box count, any API call, or auth (bearer token, `API_BASE`
`https://api.expenses.brisken.com`).

## Verify after publish

Bundle audit: the workbench chunk names `fills`, and `chunk-i18n` carries
`row.fills.label` in both languages.

On live data, note that the two loaded months were read BEFORE this shipped,
so their charges carry no `fills` yet and the strip correctly renders nothing;
a statement is parsed at upload, and the colours appear when a month is next
read. To see it, upload a workbook as a scratch month: its yellow-marked rows
show one yellow swatch on the `Amount` column, its subscription rows a gray
swatch on `Description`, and its `Card` column swatches orange or blue with no
change to any chip or count. Delete the scratch month in the same session.
