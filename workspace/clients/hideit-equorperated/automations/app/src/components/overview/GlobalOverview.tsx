import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { useState } from 'react';
import { useBoardStore } from '../../store/boardStore.ts';
import { SortableCard, KanbanCard } from '../board/Card.tsx';
import type { Card, ColumnId } from '../../types/index.ts';

const COLUMNS: { id: ColumnId; label: string }[] = [
  { id: 'backlog',     label: 'Backlog' },
  { id: 'todo',        label: 'To-Do' },
  { id: 'in-progress', label: 'In Progress' },
  { id: 'completed',   label: 'Completed' },
];

function OverviewColumn({ columnId, label, cards }: { columnId: ColumnId; label: string; cards: Card[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: columnId });
  return (
    <div className="flex flex-col w-72 flex-shrink-0">
      <div className="flex items-center gap-2 mb-3 px-1">
        <span className="flex-1 text-sm font-semibold text-gray-700 px-2 py-1 bg-gray-100 rounded">{label}</span>
        <span className="text-xs text-gray-400">{cards.length}</span>
      </div>
      <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={`flex-1 flex flex-col gap-2 min-h-[120px] p-2 rounded-xl ${isOver ? 'bg-indigo-50 border-2 border-dashed border-indigo-300' : 'bg-gray-100/60'}`}
        >
          {cards.map(card => <SortableCard key={card.id} card={card} showProjectBadge />)}
        </div>
      </SortableContext>
    </div>
  );
}

export function GlobalOverview() {
  const { projects, cards, moveCard } = useBoardStore();
  const [activeCard, setActiveCard] = useState<Card | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const getColCards = (colId: ColumnId) =>
    cards.filter(c => c.columnId === colId).sort((a, b) => a.position - b.position);

  const onDragStart = ({ active }: DragStartEvent) => {
    setActiveCard(cards.find(c => c.id === active.id) ?? null);
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    setActiveCard(null);
    if (!over || active.id === over.id) return;

    const draggedCard = cards.find(c => c.id === active.id);
    if (!draggedCard) return;

    const overId = over.id.toString();
    const COLUMN_IDS: ColumnId[] = ['backlog', 'todo', 'in-progress', 'completed'];

    if (COLUMN_IDS.includes(overId as ColumnId)) {
      const targetColumnId = overId as ColumnId;
      const colCards = getColCards(targetColumnId).filter(c => c.id !== draggedCard.id);
      const newPos = colCards.length > 0 ? colCards[colCards.length - 1].position + 1024 : 1024;
      moveCard(draggedCard.id, targetColumnId, newPos);
    } else {
      const targetCard = cards.find(c => c.id === overId);
      if (!targetCard) return;

      const targetColumnId = targetCard.columnId;
      const colCards = getColCards(targetColumnId).filter(c => c.id !== draggedCard.id);
      const targetIdx = colCards.findIndex(c => c.id === overId);

      // Insert BEFORE the hovered card
      let newPos: number;
      if (targetIdx <= 0) {
        newPos = (colCards[0]?.position ?? 1024) / 2;
      } else {
        newPos = (colCards[targetIdx - 1].position + colCards[targetIdx].position) / 2;
      }

      moveCard(draggedCard.id, targetColumnId, newPos);
    }
  };

  const totalByProject = projects.map(p => ({
    ...p,
    count: cards.filter(c => c.projectId === p.id).length,
  }));

  return (
    <div className="flex-1 overflow-x-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Global Overview</h1>
        <p className="text-sm text-gray-500 mt-1">All tasks across all projects</p>

        {/* Project summary chips */}
        <div className="flex flex-wrap gap-2 mt-3">
          {totalByProject.map(p => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm text-white font-medium"
              style={{ backgroundColor: p.color }}
            >
              {p.name}
              <span className="bg-white/30 rounded-full px-1.5 py-0.5 text-xs">{p.count}</span>
            </span>
          ))}
          {projects.length === 0 && (
            <span className="text-sm text-gray-400">No projects yet. Create one in the sidebar.</span>
          )}
        </div>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        <div className="flex gap-4 items-start pb-6">
          {COLUMNS.map(col => (
            <OverviewColumn
              key={col.id}
              columnId={col.id}
              label={col.label}
              cards={getColCards(col.id)}
            />
          ))}
        </div>
        <DragOverlay>
          {activeCard && <KanbanCard card={activeCard} showProjectBadge isDragging />}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
