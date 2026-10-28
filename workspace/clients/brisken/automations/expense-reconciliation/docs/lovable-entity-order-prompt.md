# Lovable prompt: the legal entities are a list you own

> **NOT YET APPLIED.** Paste after the item-92 backend deploy
> (`entity_order` on `PUT /api/settings`, api-contract "The writable keys").
> Pasting before it means every reorder saves a key the backend refuses:
> `400 unknown settings key(s): entity_order`.
>
> Independent of the item-91 tabs prompt. Whichever lands first, this one
> changes the Legal entities editor only, wherever that editor happens to
> live: its own tab if tabs are applied, its section of the scrolling page
> if not.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Criss books every expense against a legal entity, and the entity list is
alphabetical everywhere: in Settings and in the entity dropdown on every
expense row. Nobody chose that order. The entity she touches all day sits
wherever its initial puts it, and there is no way to move it.

Two things are wrong with the editor as it stands. It shows only the
entities somebody typed into Settings, while the dropdown offers every
entity the tool knows about, including the ones that arrive from the
provisioning file and the card map. On the live tenant that is most of
them, which is why the editor can look empty while the dropdown is full.
And the rows are a wide table where every field of every entity is on
screen at once, so the list itself is hard to read.

The backend now stores an order (`entity_order`) and serves
`entity_options` in it. This prompt makes the editor the place that order
is set.

## 1. The list shows every entity, in the saved order

Render one row per name in `entity_options` from `GET /api/settings`, in
the order the payload gives them. Not `Object.keys(entities)`, which is
the registry only, and **never sorted client-side**: the payload order is
the answer, and sorting it locally throws away the whole feature.

A row whose name has no entry in `entities` is a real entity that the
provisioning file or a card points at. It renders like any other row, with
its fields empty; filling any of them creates its registry entry on save,
which is what the editor already does for a new row.

Keep `set.entities.addRow` and the removal control exactly as they are.
Removing a row still means deleting that name from the `entities` map and
saving that map. It does not delete an entity that the provisioning file
or the card map supplies; such a row reappears with empty fields, because
the tool still knows the entity. Say so in the confirm copy
(`set.entities.removeHint`, section 5).

## 2. One row opens at a time

The row itself is the name plus a one-line summary of what is set, muted:
the org id when present, then `default_paid_through` when present, joined
with a middot. Nothing set: `set.entities.rowEmpty`.

Clicking the row opens its fields beneath it, and closes whichever row was
open. The fields are the ones the editor already has, unchanged in name,
help text, validation and save behaviour: org id, chart path, default paid
through, scope groups, account picks. Field editing still saves
`{"entities": {...the whole map...}}`, the whole map every time, exactly as
today. Reordering does not go through that key at all (section 3).

The open row is `aria-expanded`, keyboard reachable, and Enter or Space
opens it.

## 3. Reordering, and how it saves

Each row carries, in a leading cell:

- A drag handle (`GripVertical`), `aria-hidden`, on a row with
  `draggable=true`. Dragging a row onto another row drops it in that
  position. Use the browser's own drag events; **do not add a
  drag-and-drop library**.
- **Move up** and **Move down** buttons, `variant="ghost" size="sm"`,
  labels `set.entities.moveUp` / `set.entities.moveDown`. These are the
  contract: everything reorderable by drag is reorderable by button, for
  the keyboard and for a touch screen. Disabled at the ends of the list.

Either gesture saves immediately, on its own:

```
PUT /api/settings   {"entity_order": ["Corporate Services", "Cloud Services", ...]}
```

The list is every name currently rendered, top to bottom, including rows
with no registry entry. Optimistic: move the row, then save. Show the saved
confirmation only when `applied` contains `entity_order`; on a 400, or on a
200 whose `applied` does not name it, put the row back where it was and
show the error the way this page already shows a failed save. Never leave
an order on screen that the backend did not take.

There is no Save button for the order, and the order never rides along in
an `entities` save. They are two keys and two requests.

## 4. The dropdown needs no change

The per-expense entity dropdown already renders `entity_options` in payload
order, and so does the entity picker on the month pages. They follow this
order for free once the backend has it. The only thing that can break them
is a `.sort()` added on the way to a picker, so do not add one anywhere.

## 5. New strings (EN, PT-BR)

| Key | EN | PT |
|---|---|---|
| `set.entities.moveUp` | Move up | Mover para cima |
| `set.entities.moveDown` | Move down | Mover para baixo |
| `set.entities.orderHint` | Drag a row, or use the arrows, to set the order. This is the order the entity list shows everywhere, including the dropdown on each expense. | Arraste uma linha, ou use as setas, para definir a ordem. Esta é a ordem em que a lista de entidades aparece em todo lugar, inclusive na lista suspensa de cada despesa. |
| `set.entities.orderSaved` | Order saved | Ordem salva |
| `set.entities.rowEmpty` | Nothing set yet | Nada definido ainda |
| `set.entities.removeHint` | This clears what you set for this entity. An entity that comes from a card or from the accounts file stays in the list, with empty fields. | Isso limpa o que você definiu para esta entidade. Uma entidade que vem de um cartão ou do arquivo de contas continua na lista, com os campos vazios. |

`set.entities.listHelp` keeps its place above the list;
`set.entities.orderHint` goes under it.

## 6. Out of scope

- No new endpoints and no new fields beyond `entity_order`.
- Do not change what any entity field means, validates or sends.
- Do not reorder anything else on this page. Cards, merchants and cost
  centers keep the order they have.
- No multi-select, no bulk actions, no new colours.

## 7. Checking it landed

Drive it, do not read it:

1. Settings, Legal entities: the list shows every entity the expense
   dropdown offers, not only the ones with fields filled in.
2. Move the bottom entity to the top with the Move up button. The
   confirmation shows. Reload the page: it is still at the top.
3. Do the same by dragging, on a different entity.
4. Open any month, Expenses, and open an entity dropdown on a row: the
   order matches the Settings list, top to bottom.
5. Click a row: its fields open, and the row that was open closes. Edit
   the org id, save, reload: the value is there and the order has not
   moved.
6. Network tab on a reorder: one `PUT /api/settings`, its body exactly
   `{"entity_order": [...]}`, and nothing else in the request.
7. PT: switch language and walk the list. No key renders as its own name.
