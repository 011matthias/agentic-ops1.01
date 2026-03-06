import { TAG_COLORS } from '../../types/index.ts';

interface Props {
  value: string;
  onChange: (color: string) => void;
}

export function ColorPicker({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {TAG_COLORS.map(color => (
        <button
          key={color}
          onClick={() => onChange(color)}
          className="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110"
          style={{
            backgroundColor: color,
            borderColor: value === color ? '#1e293b' : 'transparent',
          }}
          aria-label={color}
        />
      ))}
    </div>
  );
}
