# Lovable prompt: "Save corrections to memory" saves only what is ticked (item 246)

> **NOT YET APPLIED.** Backend half ships with item 246: `POST
> /api/runs/{id}/commit-memory` takes `{ "keep": [lesson ids] }`, and every
> `memory-plan` lesson carries `effect`, `replaces` and `already_saved`. A
> stale SPA sends no body and gets the defaults, exactly as before, so
> publishing the backend first loses nothing.
>
> **Drive bundle-first.** On a bundle without this prompt the button saves
> immediately. Never press Save on a live month to test it.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/MemoryPlan.tsx` (the `MemoryPlanDialog`), the Publish checklist component (`PublishChecklist`), `src/lib/api.ts` and `src/lib/i18n.tsx`. No new endpoint.

## Why

The owner: "save to memory function should not be all or nothing. users should have the chance to adjust precisely what changes in each line item they want saved to memory", and "when save to memory is clicked the existing rule for that case is overwritten".

Today the dialog lists every change as a sentence and the button saves all of them. Now each sentence gets a checkbox, the dialog says which lines replace a rule memory already holds, and the save sends exactly the ticked lines.

## 1. `api.ts`

1. `MemoryLesson` (the type the Publish checklist reads from `memory-plan` `lessons[]`) gains three fields:
   ```ts
   effect: "new" | "replaces" | "same" | "adds";
   replaces: Array<{ table: string; key: Record<string, string>;
                     value: string; removed: boolean }>;
   already_saved: boolean;
   ```
   Treat a missing `effect` as `"new"`, a missing `replaces` as `[]`, a missing `already_saved` as `false`.
2. The save mutation (`commitMemory(runId)` or however it is named, `POST /api/runs/{runId}/commit-memory`) takes an optional `keep?: string[]` and, when given, sends the JSON body `{ keep }`. Its reply type gains `saved: boolean`, `reason?: string`, `lessons?: { kept: string[]; skipped: string[]; already_saved: string[]; refused_owner_gated: string[]; unknown: string[]; unresolved_conflicts: string[] }`, and `learned.rules_replaced?: number`.

## 2. `MemoryPlanDialog`: a checkbox per line

Keep the item-225 layout (sentences in sections inside the scroll box). Changes:

1. **Every lesson is a row with a checkbox** (shadcn `Checkbox`, `aria-label` = the lesson's `description`), the sentence beside it. One state: `ticked: Set<string>` of lesson ids, initialised once per open from the lessons where `default_keep === true && owner_gated !== true && already_saved !== true`.
2. **Sections**, in this order, each only when non-empty, heading with the count in parentheses (same heading style as today):
   - `mplan.sec.rules` "Your corrections": `kind === "correction"`, `table !== "registry"`, not `already_saved`.
   - `mplan.sec.merchants` "Merchant list": `kind === "correction"`, `table === "registry"`.
   - `mplan.sec.choose` "Choose one": `kind === "conflict"` or `kind === "drift"`, grouped by `conflict_group` exactly as the Publish checklist groups them (the group's rows under one muted line `mplan.sec.choose.sub`). These start unticked. Ticking two of one group saves neither; say so in that muted line, do not enforce it.
   - `mplan.sec.saved` "Already saved from this month": `already_saved === true`, muted text, unticked. They can be ticked; the backend skips them and the toast says so.
3. **Owner-gated** lessons (`owner_gated === true`) show with the checkbox disabled and the sentence muted. Their sentence already ends with "Held for the owner".
4. **An effect badge** before the sentence, small (`text-[10px] px-1.5 py-0.5 rounded`):
   - `effect === "replaces"`: `mplan.badge.replaces` "Replaces", amber (`bg-amber-100 text-amber-900`, dark `bg-amber-900/40 text-amber-200`). The sentence already ends with "Replaces …" naming the old rule; a `removed: true` entry is a rule under another spelling of the same merchant that the save deletes.
   - `effect === "new"`: `mplan.badge.new` "New", neutral outline.
   - `effect === "same"`: `mplan.badge.same` "Already in memory", muted.
   - `effect === "adds"`: no badge.
5. **Above the sections**, one line of two text buttons: `mplan.tickNone` "Untick all" and `mplan.tickReset` "Back to suggested" (restores the initial set).
6. **Footer**: Cancel, and the save button `t("mplan.save", { n: ticked.size })` ("Save {n} changes"), disabled when `ticked.size === 0`. It calls the save mutation with `keep: [...ticked]`. When there is nothing tickable at all, show Close only, as today.
7. **After the save**, toast:
   - `saved === false && reason === "nothing_to_save"`: `mplan.toast.nothing` "Nothing new to save: memory already holds these."
   - otherwise the existing saved toast, and when `learned.rules_replaced > 0` append `mplan.toast.replaced` "Replaced {n} older rules."
   - when `lessons.unresolved_conflicts.length > 0` append `mplan.toast.unresolved` "Rows you ticked disagree, so {n} were not saved."

Fallback: when the reply has no `lessons` array (an older backend), render today's dialog unchanged and send no body.

## 3. Publish checklist

Show the same effect badge (point 2.4) before each sentence. Nothing else changes: it already starts from `default_keep`, so lessons this month already saved start unticked there too.

## 4. Strings

| Key | EN | PT-BR |
|---|---|---|
| `mplan.sec.choose` | Choose one ({n}) | Escolha uma ({n}) |
| `mplan.sec.choose.sub` | These rows disagree, or would change an account already decided. Tick the one to remember; ticking two of one group saves neither. | Estas linhas discordam, ou mudariam uma conta já decidida. Marque a que deve ser lembrada; marcar duas do mesmo grupo não salva nenhuma. |
| `mplan.sec.saved` | Already saved from this month ({n}) | Já salvas deste mês ({n}) |
| `mplan.badge.replaces` | Replaces | Substitui |
| `mplan.badge.new` | New | Nova |
| `mplan.badge.same` | Already in memory | Já na memória |
| `mplan.tickNone` | Untick all | Desmarcar tudo |
| `mplan.tickReset` | Back to suggested | Voltar ao sugerido |
| `mplan.toast.nothing` | Nothing new to save: memory already holds these. | Nada novo para salvar: a memória já tem isto. |
| `mplan.toast.replaced` | Replaced {n} older rules. | {n} regras antigas substituídas. |
| `mplan.toast.unresolved` | Rows you ticked disagree, so {n} were not saved. | As linhas marcadas discordam, então {n} não foram salvas. |

`mplan.sec.notSaved` and `mplan.sec.notSaved.sub` are no longer used by the dialog (everything can now be ticked there). Delete them only if a project search shows nothing else uses them. The sentences themselves come from the backend in English.

## 5. Do not change

- The Memory page and its saves table, the undo.
- The Publish button's own flow, beyond the badge in point 3.
- The "Save corrections to memory" button and its tooltip on the Expenses page.

## Checking it landed

Open the dialog on April 2026 Expenses (`/expenses/0603bb0e6f38`) and press Cancel; do not press Save.

1. Every sentence has a checkbox; the number of checkboxes equals `memory-plan` `lessons.length` for that month.
2. The ticked ones are exactly the lessons with `default_keep: true`, not owner-gated, not already saved; the save button's count matches.
3. "Untick all" disables the save button; "Back to suggested" restores the count.
4. Every lesson with `effect: "replaces"` shows the amber "Replaces" badge.
````
