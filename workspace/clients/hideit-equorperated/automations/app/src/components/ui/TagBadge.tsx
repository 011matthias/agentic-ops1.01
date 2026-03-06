import type { Tag } from '../../types/index.ts';

interface Props {
  tag: Tag;
  onRemove?: () => void;
}

export function TagBadge({ tag, onRemove }: Props) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: tag.color }}
    >
      {tag.name}
      {onRemove && (
        <button onClick={onRemove} className="hover:opacity-75 leading-none">×</button>
      )}
    </span>
  );
}
