# Lovable prompt: reorder legal entities by press, hold and drag (item 92, round 2)

> **NOT YET APPLIED.** No backend change: `entity_order` is live since v146
> and round 1 (`lovable-entity-order-prompt.md`) is applied. This round
> replaces how a row is moved, nothing else.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

The Legal entities list in Settings can be reordered today with Move up /
Move down arrows, or with the browser's built-in drag. The owner wants it to
feel like a normal sortable list: click, hold, drag the row where it goes,
let go. The arrows go.

The browser's built-in drag cannot do that. It drags a faded ghost image
instead of the row, leaves the other rows standing still until the drop, and
does nothing on a touch screen. So this round moves the list to
`@dnd-kit`.

## 1. Swap the drag mechanism

Add `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` and
`@dnd-kit/modifiers`. Use them in the Legal entities editor only.

Remove from that editor: the `draggable` attribute, the native
`onDragStart` / `onDragOver` / `onDrop` handlers, and the Move up / Move down
buttons with their handlers. Leave the `set.entities.moveUp` /
`set.entities.moveDown` keys in the dictionary, unused.

Structure: one `DndContext` around the list, a `SortableContext` over the
row names with `verticalListSortingStrategy`, one `useSortable({ id: name })`
per row. Modifiers `restrictToVerticalAxis` and `restrictToParentElement`.

## 2. Press and hold lifts the row

Sensors, exactly these:

- `MouseSensor` with `activationConstraint: { delay: 200, tolerance: 5 }`
- `TouchSensor` with `activationConstraint: { delay: 250, tolerance: 5 }`
- `KeyboardSensor` with `coordinateGetter: sortableKeyboardCoordinates`

Mouse and Touch rather than `PointerSensor`, on purpose: `PointerSensor`
needs `touch-action: none` on the row, which stops a phone from scrolling
the page when a finger lands on the list. With the delay, a swipe still
scrolls and a long press picks the row up. Do not set `touch-action: none`.

**Where a press can start a drag:** the row's header bar only (the grip,
the name, the summary line). Never inside an open row's fields: pressing in
an input has to select text, not lift the row. Put the mouse and touch
listeners on the header bar.

**Click still opens the row.** A press released before 200 ms is a click and
opens or closes the row exactly as today. A press that turned into a drag
must not also toggle the row when it is released: swallow the click that
follows a drag end.

**Dragging an open row closes it first.** On drag start, close any open row,
so what lifts is the one-line header.

**Keyboard, now that the arrows are gone.** The `GripVertical` icon at the
row's left edge becomes a real focusable handle: a `button`,
`aria-label` `set.entities.dragHandle` with `{name}`, carrying the sortable
`attributes`, the keyboard listener and `setActivatorNodeRef`. Space picks
the row up, the arrow keys move it, Space drops, Escape cancels. The header
bar keeps its own Enter / Space to open the row; keyboard drag lives on the
handle only, so the two never collide.

## 3. What a drag looks like

- Cursor `grab` over the header bar, `grabbing` while a row is lifted.
- The lifted row renders in a `DragOverlay` so it follows the pointer and is
  never clipped by the card: same content as the header bar, `bg-background`,
  `shadow-lg`, `scale-[1.02]`, rounded like the row.
- The slot it left stays in the list as a placeholder at the row's height:
  `opacity-40` with a dashed border.
- The other rows slide aside as it passes, using the sortable `transform` and
  `transition` (`CSS.Transform.toString`), about 200 ms.
- `select-none` on the header bar so a hold never highlights text.
- Dragging near the top or bottom of the window scrolls it (dnd-kit's default
  auto-scroll, leave it on).

## 4. Saving is unchanged from round 1

On `onDragEnd`:

- Dropped where it started, dropped outside the list, or cancelled with
  Escape: nothing happens and **no request is sent**.
- Otherwise: `arrayMove` the names, show the new order at once, then
  `PUT /api/settings` with `{"entity_order": [...]}` alone, every rendered
  name top to bottom. Success only when `applied` contains `entity_order`;
  on a 400, or a 200 whose `applied` does not name it, put the previous
  order back and show `set.save.nothing`, as round 1 does.
- While that save is in flight, dragging is disabled (`useSortable`
  `disabled`), so two drops can never race each other to the server. It is
  one short request.

## 5. Screen reader announcements

Pass `accessibility.screenReaderInstructions` and `announcements` to
`DndContext`, from these keys. `{n}` is 1-based, `{total}` the row count.

| Event | Key |
|---|---|
| instructions | `set.entities.dnd.instructions` |
| `onDragStart` | `set.entities.dnd.picked` |
| `onDragOver` | `set.entities.dnd.moved` |
| `onDragEnd` | `set.entities.dnd.dropped` |
| `onDragCancel` | `set.entities.dnd.cancelled` |

## 6. Strings (EN, PT-BR)

| Key | EN | PT |
|---|---|---|
| `set.entities.orderHint` (replaces the current text) | Click and hold a row, then drag it to set the order. This is the order the entity list shows everywhere, including the dropdown on each expense. | Clique e segure uma linha e arraste para definir a ordem. Esta é a ordem em que a lista de entidades aparece em todo lugar, inclusive na lista suspensa de cada despesa. |
| `set.entities.dragHandle` | Reorder {name} | Reordenar {name} |
| `set.entities.dnd.instructions` | To reorder with the keyboard, press Space on the handle, move with the arrow keys, then press Space again to drop it, or Escape to cancel. | Para reordenar pelo teclado, pressione Espaço na alça, mova com as setas e pressione Espaço de novo para soltar, ou Esc para cancelar. |
| `set.entities.dnd.picked` | Picked up {name}. | {name} selecionada. |
| `set.entities.dnd.moved` | {name} moved to position {n} of {total}. | {name} movida para a posição {n} de {total}. |
| `set.entities.dnd.dropped` | {name} dropped at position {n} of {total}. | {name} solta na posição {n} de {total}. |
| `set.entities.dnd.cancelled` | Reordering cancelled. {name} is back at position {n}. | Reordenação cancelada. {name} voltou para a posição {n}. |

## 7. Do not change

- Which entities the list shows and in what order it loads (`entity_options`,
  never sorted locally).
- Opening a row, its fields, Save entities, Add entity, Remove.
- The save contract in section 4, the tabs, anything outside this editor.
- No other list on the page becomes draggable.

## 8. Checking it landed

Drive it, do not read it:

1. Hover a row's header: grab cursor. A quick click opens the row and a
   second quick click closes it. Nothing lifts.
2. Press and hold on a closed row, then move: after a moment the row lifts
   with a shadow and follows the pointer, and the rows it passes slide
   aside. Drop it two places lower. Network: exactly one
   `PUT /api/settings`, body only `{"entity_order": [...]}`. Reload: the order
   held.
3. Press and move straight away without holding: the row does not lift.
4. Open a row, then press and hold its header and drag: it closes as it
   lifts. Press inside one of its fields and drag instead: text selects,
   nothing lifts.
5. Lift a row and drop it where it was, or press Escape mid-drag: it settles
   back and no request is sent.
6. Keyboard only: Tab to a row's handle, Space, ArrowDown twice, Space. The
   row moved two places and saved.
7. No Move up / Move down buttons anywhere in the editor.
8. Open a month's Expenses: the entity dropdown follows the new order.
9. At 390 px wide: a swipe over the list scrolls the page; a long press then
   drag reorders.
10. PT: the hint and the handle's label are translated.
