import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import type { CustomAttribute } from '../../types/index.ts';

interface Props {
  attributes: CustomAttribute[];
  onChange: (attrs: CustomAttribute[]) => void;
}

export function AttributeEditor({ attributes, onChange }: Props) {
  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');

  const add = () => {
    if (!newKey.trim()) return;
    onChange([...attributes, { key: newKey.trim(), value: newVal.trim() }]);
    setNewKey('');
    setNewVal('');
  };

  const update = (idx: number, field: 'key' | 'value', val: string) => {
    onChange(attributes.map((a, i) => i === idx ? { ...a, [field]: val } : a));
  };

  const remove = (idx: number) => {
    onChange(attributes.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-2">
      {attributes.map((attr, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <input
            className="flex-1 px-2 py-1 text-sm border border-gray-200 rounded bg-gray-50 focus:outline-none focus:border-indigo-400"
            value={attr.key}
            onChange={e => update(idx, 'key', e.target.value)}
            placeholder="Key"
          />
          <span className="text-gray-400">:</span>
          <input
            className="flex-[2] px-2 py-1 text-sm border border-gray-200 rounded bg-gray-50 focus:outline-none focus:border-indigo-400"
            value={attr.value}
            onChange={e => update(idx, 'value', e.target.value)}
            placeholder="Value"
            title={attr.key === 'Deadline' ? 'Use YYYY-MM-DD format for deadline scanning' : undefined}
          />
          <button onClick={() => remove(idx)} className="text-gray-400 hover:text-red-500">
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <div className="flex gap-2 items-center">
        <input
          className="flex-1 px-2 py-1 text-sm border border-dashed border-gray-300 rounded bg-white focus:outline-none focus:border-indigo-400"
          value={newKey}
          onChange={e => setNewKey(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="New key (e.g. Deadline)"
        />
        <span className="text-gray-400">:</span>
        <input
          className="flex-[2] px-2 py-1 text-sm border border-dashed border-gray-300 rounded bg-white focus:outline-none focus:border-indigo-400"
          value={newVal}
          onChange={e => setNewVal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Value"
        />
        <button onClick={add} className="text-indigo-500 hover:text-indigo-700">
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}
