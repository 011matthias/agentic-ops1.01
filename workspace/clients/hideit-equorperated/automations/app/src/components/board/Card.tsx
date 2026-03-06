import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, AlertCircle } from 'lucide-react';
import type { Card as CardType } from '../../types/index.ts';
import { TagBadge } from '../ui/TagBadge.tsx';
import { useUIStore } from '../../store/uiStore.ts';
import { useBoardStore } from '../../store/boardStore.ts';

interface Props {
  card: CardType;
  showProjectBadge?: boolean;
  isDragging?: boolean;
}

export function KanbanCard({ card, showProjectBadge, isDragging }: Props) {
  const openCardModal = useUIStore(s => s.openCardModal);
  const projects = useBoardStore(s => s.projects);
  const project = projects.find(p => p.id === card.projectId);

  const deadline = card.attributes.find(a => a.key === 'Deadline');
  const isOverdue = deadline && new Date(deadline.value).getTime() < Date.now();

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 shadow-sm p-3 cursor-pointer group hover:border-indigo-300 hover:shadow-md transition-all ${isDragging ? 'opacity-40 border-dashed border-indigo-400' : ''}`}
      onClick={() => openCardModal(card.id)}
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 leading-snug">{card.title}</p>
          {card.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{card.description}</p>
          )}
        </div>
        <GripVertical size={14} className="text-gray-300 group-hover:text-gray-400 flex-shrink-0 mt-0.5" />
      </div>

      {(card.tags.length > 0 || showProjectBadge || deadline) && (
        <div className="flex flex-wrap gap-1 mt-2 items-center">
          {showProjectBadge && project && (
            <span
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold text-white"
              style={{ backgroundColor: project.color }}
            >
              {project.name}
            </span>
          )}
          {card.tags.map(t => <TagBadge key={t.id} tag={t} />)}
          {deadline && (
            <span className={`inline-flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded ${isOverdue ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
              {isOverdue && <AlertCircle size={10} />}
              {deadline.value}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function SortableCard({ card, showProjectBadge }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id });
  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
    >
      <KanbanCard card={card} showProjectBadge={showProjectBadge} isDragging={isDragging} />
    </div>
  );
}
