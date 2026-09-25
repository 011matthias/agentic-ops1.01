# Lovable prompt: Publish shows what it will remember (backlog item 183, half A)

Paste into Lovable. The backend is live once the item-183A PR deploys; every
field below exists on the API. One screen changes: the month page's Publish
button (`RunWorkbench.tsx`, `onPublish` from `SummaryBar`). Unpublish is
unchanged.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com`
(`API_BASE` in `src/lib/api.ts`). Change ONLY what is described here.

## What changes

Publishing a month also saves that month's corrections to memory. Until now
that happened silently. Now Publish first shows a checklist of what it will
remember, one line per lesson, and saves only the ticked ones.

## 1. API

In `src/lib/api.ts`:

1. `getMemoryPlan(runId)` already calls `GET /api/runs/{runId}/memory-plan`.
   Add to its reply type:
   ```ts
   lessons: Array<{
     id: string;                 // send back as-is
     kind: "correction" | "conflict";
     table: string;              // "merchant_category", "field_correction", "registry", ...
     key: Record<string, string>;
     description: string;        // plain English sentence, show as-is
     sources: Array<{ document_id: string; kind: "receipt" | "charge";
                      vendor: string; date: string; total: string;
                      currency: string; line_index?: number }>;
     default_keep: boolean;      // the checkbox's starting state
     owner_gated: boolean;       // show, but never tickable
     conflict_group: string;     // "" unless kind === "conflict"
   }>;
   ```
2. `publishRun(runId, publish, opts)`: accept `opts.keep?: string[]`. When
   publishing, send the body `{ override?: true, keep: [...] }` (include
   `keep` whenever the caller passed it, even as an empty array; include
   `override` only when true, as today). Extend the reply's `memory.learned`
   type with
   `lessons?: { kept: string[]; skipped: string[]; refused_owner_gated: string[]; unknown: string[]; unresolved_conflicts: string[]; already_saved?: string[] }`.
   `learned` is no longer only numbers, so type it as
   `Record<string, unknown>` and read the counts with `Number(...) || 0`.

## 2. The checklist dialog

In `RunWorkbench.tsx`, change the `onPublish` handler: when the month is NOT
published, do not call `publish.mutate` straight away. Open a new dialog,
`PublishChecklistDialog` (new file `src/components/PublishChecklist.tsx`),
passing `runId` and the `override` flag `SummaryBar` handed over. Unpublish
keeps calling `publish.mutate({ next: false })` directly.

The dialog:

- On open, load `getMemoryPlan(runId)` with react-query (key
  `["memory-plan", runId]`, `staleTime: 0`). While loading, a spinner and the
  line "Checking what this month teaches..." / "Verificando o que este mês
  ensina...".
- If `lessons` is empty, do not show the dialog at all: publish at once with
  `keep: []`, exactly as today's button did.
- Title: "Publish and remember" / "Publicar e memorizar".
- One sentence under the title: "Publishing saves the corrections you tick
  below, so next month fills them in. Untick anything that was a one-off."
  / "Publicar salva as correções marcadas abaixo, para o próximo mês já vir
  preenchido. Desmarque o que foi exceção."
- **Corrections** (`kind === "correction"`), one row each, in the order the
  API returns them:
  - a checkbox, starting at `default_keep`;
  - the `description` text as-is;
  - under it, small muted text listing `sources`: `vendor total currency
    date` for each, comma separated, at most three, then "and N more" / "e
    mais N". A source with `kind === "charge"` gets the prefix "Charge:" /
    "Lançamento:".
  - When `owner_gated` is true: the checkbox is unchecked AND disabled, and
    the row carries a grey badge "Held for the owner" / "Reservado ao
    responsável" with the tooltip "OpenAI, Anthropic and Lovable are added to
    the merchant list by the owner only." / "OpenAI, Anthropic e Lovable só
    entram na lista de comerciantes pelo responsável."
- **Conflicts** (`kind === "conflict"`), in their own section BELOW the
  corrections, only when there is at least one:
  - Section heading "These rows disagree" / "Estas linhas discordam", with
    the line "Nothing is remembered for these unless you pick one option."
    / "Nada é memorizado aqui a menos que você escolha uma opção."
  - Group the lessons by `conflict_group`; each group is one amber-bordered
    box (`border-amber-400 bg-amber-50`, dark mode `border-amber-600
    bg-amber-950/30`).
  - Inside a box, each lesson is a checkbox row with its `description` and
    `sources`, starting UNCHECKED (`default_keep` is false). Ticking one
    option in a box unticks the others in the same box (radio behaviour,
    but the user can also untick all).
  - `owner_gated` rows: disabled, same badge as above.
- Footer:
  - left, muted: "N of M will be remembered" / "N de M serão memorizadas",
    counting ticked rows over all rows that are not `owner_gated`;
  - right: Cancel, and a primary button "Publish" / "Publicar". Publish
    stays enabled with ZERO ticked: publishing with nothing remembered is
    allowed.
- Publish calls `publish.mutate({ next: true, override, keep: [ticked ids] })`
  (pass `keep` through `publishRun`), then closes the dialog.

## 3. After publishing

In `publish.onSuccess` (publish branch), keep today's toasts, and add:

- When `memory.learned.lessons.refused_owner_gated` is non-empty, an info
  toast: "N merchant-list change(s) held for the owner." / "N alteração(ões)
  da lista de comerciantes reservada(s) ao responsável."
- When `memory.learned.lessons.unresolved_conflicts` is non-empty, a warning
  toast: "Two options of the same disagreement were ticked, so neither was
  remembered." / "Duas opções da mesma divergência foram marcadas, então
  nenhuma foi memorizada."

The count in today's "published and saved" toast already reads what was
WRITTEN, so a skipped lesson is not counted there.

## Do not

- Do not change the Unpublish path or the "Save corrections to memory"
  dialog (`MemoryPlanDialog`).
- Do not re-sort, rename or re-word `description`: it is the backend's.
- Do not persist the ticks anywhere: an unticked lesson is offered again the
  next time the month is published.
````

## Checks after publishing (for the agent, not for Lovable)

1. Bundle: `PublishChecklist`, `refused_owner_gated`, `conflict_group` and
   the PT string "Estas linhas discordam" present.
2. Never drive Publish on a live month to verify this: a working dialog
   still publishes Criss's month and writes memory. Drive the dialog up to
   the Publish button and read it, then Cancel; or verify on a `TEST -`
   scratch batch deleted in the same session.
3. The rows read in the dialog equal `GET /api/runs/{id}/memory-plan`
   `lessons[]` for that month (ids, order, default ticks).
