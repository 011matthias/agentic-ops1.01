import { useEffect, useRef, useState } from 'react';
import { X, Trash2, Tag as TagIcon, Plus } from 'lucide-react';
import { useBoardStore } from '../../store/boardStore.ts';
import { useUIStore } from '../../store/uiStore.ts';
import { AttributeEditor } from '../ui/AttributeEditor.tsx';
import { TagBadge } from '../ui/TagBadge.tsx';
import { ColorPicker } from '../ui/ColorPicker.tsx';
import type { Tag } from '../../types/index.ts';
import { TAG_COLORS } from '../../types/index.ts';

export function CardModal() {
  const activeModal = useUIStore(s => s.activeModal);
  const closeModal  = useUIStore(s => s.closeModal);
  const { cards, projects, updateCard, deleteCard } = useBoardStore();

  const [newTagName, setNewTagName]   = useState('');
  const [newTagColor, setNewTagColor] = useState(TAG_COLORS[0]);
  const [showTagAdd, setShowTagAdd]   = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeModal(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closeModal]);

  if (activeModal?.type !== 'card') return null;
  const card    = cards.find(c => c.id === activeModal.cardId);
  const project = card ? projects.find(p => p.id === card.projectId) : null;
  if (!card) return null;

  const handleAddTag = () => {
    if (!newTagName.trim()) return;
    const tag: Tag = {
      id:    `tag_${Math.random().toString(36).slice(2, 9)}`,
      name:  newTagName.trim(),
      color: newTagColor,
    };
    updateCard(card.id, { tags: [...card.tags, tag] });
    setNewTagName('');
    setShowTagAdd(false);
  };

  const handleRemoveTag = (tagId: string) => {
    updateCard(card.id, { tags: card.tags.filter(t => t.id !== tagId) });
  };

  const handleDelete = () => {
    deleteCard(card.id);
    closeModal();
  };

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === overlayRef.current) closeModal(); }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-start gap-3 p-5 border-b border-gray-100">
          {project && (
            <span
              className="mt-1 inline-block w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: project.color }}
              title={project.name}
            />
          )}
          <input
            className="flex-1 text-lg font-semibold text-gray-900 bg-transparent border-none outline-none resize-none"
            value={card.title}
            onChange={e => updateCard(card.id, { title: e.target.value })}
            placeholder="Card title"
          />
          <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Description
            </label>
            <textarea
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:border-indigo-400 resize-none"
              rows={3}
              value={card.description}
              onChange={e => updateCard(card.id, { description: e.target.value })}
              placeholder="Add a description..."
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Tags
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {card.tags.map(t => (
                <TagBadge key={t.id} tag={t} onRemove={() => handleRemoveTag(t.id)} />
              ))}
              <button
                onClick={() => setShowTagAdd(v => !v)}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs text-gray-500 border border-dashed border-gray-300 hover:border-indigo-400 hover:text-indigo-600"
              >
                <Plus size={10} /> Add tag
              </button>
            </div>
            {showTagAdd && (
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
                <input
                  className="w-full px-2 py-1 text-sm border border-gray-200 rounded bg-white focus:outline-none focus:border-indigo-400"
                  value={newTagName}
                  onChange={e => setNewTagName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAddTag()}
                  placeholder="Tag name"
                  autoFocus
                />
                <ColorPicker value={newTagColor} onChange={setNewTagColor} />
                <button
                  onClick={handleAddTag}
                  className="w-full py-1 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600"
                >
                  Add
                </button>
              </div>
            )}
          </div>

          {/* Custom Attributes */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Fields
              <span className="ml-1 text-gray-400 normal-case font-normal">(use "Deadline: YYYY-MM-DD" for reminders)</span>
            </label>
            <AttributeEditor
              attributes={card.attributes}
              onChange={attrs => updateCard(card.id, { attributes: attrs })}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-4 border-t border-gray-100">
          <div className="text-xs text-gray-400">
            {project?.name} · {card.columnId}
          </div>
          <button
            onClick={handleDelete}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>
    </div>
  );
}
