---
id: app1
name: OmniBoard Frontend
type: app
stage: build
orchestrator: none
version: 1.0
created: 2026-03-05
updated: 2026-03-05
trigger: manual (browser)
systems: [hono-api, localStorage]
last_changes: Initial spec
next_steps: Scaffold Vite project, install deps, build components in order
---

# OmniBoard Frontend

React + Vite + Tailwind single-page Kanban app.

## Tech Stack

- React 18 + Vite 5
- Tailwind CSS v3
- Lucide-React (icons)
- dnd-kit (drag-and-drop)
- Zustand (state management + localStorage persistence)
- TypeScript

## Component Hierarchy

```
App.tsx
├── AppShell.tsx                        # flex layout
│   ├── Sidebar.tsx                     # project list + Global Overview link
│   └── [main content]
│       ├── Board.tsx                   # DndContext, renders 4 Column components
│       │   ├── Column.tsx (x4)         # SortableContext, inline column rename
│       │   │   └── Card.tsx (xN)       # useSortable, tag badges, attribute preview
│       │   └── DragOverlay > Card.tsx  # ghost during active drag
│       └── GlobalOverview.tsx          # all cards from all projects
│
└── CardModal.tsx                       # portal, shown on card click
    ├── title input, description textarea
    ├── TagEditor (toggle tags)
    ├── AttributeEditor (key-value rows, "Deadline" is magic)
    └── delete button
```

## State (Zustand)

### boardStore (persisted to localStorage + synced to API)

```typescript
interface BoardStore {
  projects: Project[];
  cards: Card[];
  activeProjectId: string | null;
  isGlobalOverview: boolean;
  createProject(name: string, color: string): void;
  updateProject(id: string, patch: Partial<Project>): void;
  deleteProject(id: string): void;
  createCard(projectId: string, columnId: ColumnId, title: string): void;
  updateCard(id: string, patch: Partial<Card>): void;
  moveCard(cardId: string, targetColumnId: ColumnId, newPosition: number): void;
  deleteCard(id: string): void;
  renameColumn(projectId: string, columnId: ColumnId, newLabel: string): void;
}
```

### uiStore (ephemeral)

```typescript
interface UIStore {
  activeModal: { type: 'card'; cardId: string } | null;
  openCardModal(cardId: string): void;
  closeModal(): void;
}
```

## Data Fetching

- On app load: `GET /api/projects` + `GET /api/cards` → seed store
- On store mutations: optimistic update store → async API call → revert on error
- Offline fallback: Zustand `persist` middleware writes to `localStorage` on every mutation

## API Client (`src/api/client.ts`)

```typescript
const BASE = 'http://localhost:3001/api';
export const api = {
  projects: { list, create, update, delete },
  cards: { list, create, update, move, delete },
  boardState: { get },
};
```

## Key Behaviors

- **Column rename:** Double-click column header → inline `<input>` → blur/Enter saves → `PATCH /api/projects/:id`
- **Drag-and-drop:** dnd-kit `DndContext` wraps all columns; `onDragEnd` calls `moveCard` with fractional position
- **Global Overview:** aggregates all projects' cards; project badge colored with `project.color`; drag-to-move syncs back
- **Custom attributes:** free-form key-value pairs; `Deadline` key (case-sensitive) shows deadline badge on card
- **Tag colors:** fixed 12-color palette (Tailwind swatches)
- **New card:** "+" button in column footer → inline title input → Enter creates card

## Acceptance Criteria

- [ ] Create/rename/delete projects from sidebar
- [ ] 4 columns per project; column labels editable inline
- [ ] Cards can be dragged within a column (reorder) and across columns
- [ ] Card modal shows/edits: title, description, tags, custom attributes
- [ ] Global Overview shows all cards from all projects with project color badge
- [ ] Moving a card in Global Overview updates its column in the original project
- [ ] SQLite persists across browser refresh (server must be running)
- [ ] App loads from localStorage if server is down
