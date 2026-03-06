import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { useBoardStore } from '../../store/boardStore.ts';
import { Column } from './Column.tsx';
import { KanbanCard } from './Card.tsx';
import type { Card, ColumnId } from '../../types/index.ts';

interface Props {
  projectId: string;
}

export function Board({ projectId }: Props) {
  const { projects, cards, moveCard } = useBoardStore();
  const project = projects.find(p => p.id === projectId);
  const [activeCard, setActiveCard] = useState<Card | null>(null);
  const [overId, setOverId]         = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (!project) return <div className="p-8 text-gray-400">Project not found.</div>;

  const projectCards = cards.filter(c => c.projectId === projectId);

  const getColumnCards = (columnId: ColumnId) =>
    projectCards.filter(c => c.columnId === columnId).sort((a, b) => a.position - b.position);

  const onDragStart = ({ active }: DragStartEvent) => {
    setActiveCard(projectCards.find(c => c.id === active.id) ?? null);
  };

  const onDragOver = ({ over }: DragOverEvent) => {
    setOverId(over?.id?.toString() ?? null);
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    setActiveCard(null);
    setOverId(null);
    if (!over || active.id === over.id) return;

    const draggedCard = projectCards.find(c => c.id === active.id);
    if (!draggedCard) return;

    const overId = over.id.toString();
    const COLUMN_IDS: ColumnId[] = ['backlog', 'todo', 'in-progress', 'completed'];

    if (COLUMN_IDS.includes(overId as ColumnId)) {
      // Dropped onto column — place at end
      const targetColumnId = overId as ColumnId;
      const colCards = getColumnCards(targetColumnId).filter(c => c.id !== draggedCard.id);
      const newPos = colCards.length > 0 ? colCards[colCards.length - 1].position + 1024 : 1024;
      moveCard(draggedCard.id, targetColumnId, newPos);
    } else {
      // Dropped onto another card
      const targetCard = projectCards.find(c => c.id === overId);
      if (!targetCard) return;

      const targetColumnId = targetCard.columnId;
      const colCards = getColumnCards(targetColumnId).filter(c => c.id !== draggedCard.id);
      const targetIdx = colCards.findIndex(c => c.id === overId);

      // Insert BEFORE the hovered card (standard Kanban UX)
      let newPos: number;
      if (targetIdx <= 0) {
        // Before the first card
        newPos = (colCards[0]?.position ?? 1024) / 2;
      } else {
        // Between targetIdx-1 and targetIdx
        newPos = (colCards[targetIdx - 1].position + colCards[targetIdx].position) / 2;
      }

      moveCard(draggedCard.id, targetColumnId, newPos);
    }
  };

  return (
    <div className="flex-1 overflow-x-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
      </div>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDragEnd={onDragEnd}
      >
        <div className="flex gap-4 items-start pb-6">
          {project.columns.map(col => (
            <Column
              key={col.id}
              column={col}
              cards={getColumnCards(col.id)}
              projectId={projectId}
            />
          ))}
        </div>

        <DragOverlay>
          {activeCard && <KanbanCard card={activeCard} isDragging />}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
