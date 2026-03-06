import { useState, useRef } from 'react';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { Plus } from 'lucide-react';
import type { Card, ColumnDef } from '../../types/index.ts';
import { SortableCard } from './Card.tsx';
import { useBoardStore } from '../../store/boardStore.ts';

interface Props {
  column: ColumnDef;
  cards: Card[];
  projectId: string;
}

const COLUMN_COLORS: Record<string, string> = {
  backlog:      'bg-gray-100 text-gray-600',
  todo:         'bg-blue-100 text-blue-700',
  'in-progress':'bg-amber-100 text-amber-700',
  completed:    'bg-green-100 text-green-700',
};

export function Column({ column, cards, projectId }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const { renameColumn, createCard } = useBoardStore();
  const [editing, setEditing]     = useState(false);
  const [label, setLabel]         = useState(column.label);
  const [addingTitle, setAddingTitle] = useState('');
  const [isAdding, setIsAdding]   = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const saveLabel = () => {
    if (label.trim() && label.trim() !== column.label) {
      renameColumn(projectId, column.id, label.trim());
    } else {
      setLabel(column.label);
    }
    setEditing(false);
  };

  const handleAddCard = () => {
    if (addingTitle.trim()) {
      createCard(projectId, column.id, addingTitle.trim());
    }
    setAddingTitle('');
    setIsAdding(false);
  };

  const cardIds = cards.map(c => c.id);

  return (
    <div className="flex flex-col w-72 flex-shrink-0">
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        {editing ? (
          <input
            ref={inputRef}
            className="flex-1 px-2 py-1 text-sm font-semibold border border-indigo-400 rounded outline-none bg-white"
            value={label}
            onChange={e => setLabel(e.target.value)}
            onBlur={saveLabel}
            onKeyDown={e => { if (e.key === 'Enter') saveLabel(); if (e.key === 'Escape') { setLabel(column.label); setEditing(false); } }}
            autoFocus
          />
        ) : (
          <button
            className={`flex-1 text-left px-2 py-1 text-sm font-semibold rounded ${COLUMN_COLORS[column.id] ?? 'bg-gray-100 text-gray-600'}`}
            onDoubleClick={() => setEditing(true)}
            title="Double-click to rename"
          >
            {column.label}
          </button>
        )}
        <span className="text-xs text-gray-400 font-medium">{cards.length}</span>
      </div>

      {/* Cards area */}
      <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={`flex-1 flex flex-col gap-2 min-h-[120px] p-2 rounded-xl transition-colors ${isOver ? 'bg-indigo-50 border-2 border-dashed border-indigo-300' : 'bg-gray-100/60'}`}
        >
          {cards
            .sort((a, b) => a.position - b.position)
            .map(card => <SortableCard key={card.id} card={card} />)
          }

          {/* Inline add card */}
          {isAdding ? (
            <div className="bg-white rounded-lg border border-indigo-300 p-2 shadow-sm">
              <input
                className="w-full text-sm outline-none"
                value={addingTitle}
                onChange={e => setAddingTitle(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAddCard(); if (e.key === 'Escape') setIsAdding(false); }}
                placeholder="Card title..."
                autoFocus
                onBlur={handleAddCard}
              />
            </div>
          ) : (
            <button
              onClick={() => setIsAdding(true)}
              className="flex items-center gap-1 w-full px-2 py-1.5 text-xs text-gray-400 hover:text-indigo-600 hover:bg-white/70 rounded-lg transition-colors"
            >
              <Plus size={12} /> Add card
            </button>
          )}
        </div>
      </SortableContext>
    </div>
  );
}
