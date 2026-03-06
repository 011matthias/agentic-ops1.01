export type ColumnId = 'backlog' | 'todo' | 'in-progress' | 'completed';

export interface Tag {
  id: string;
  name: string;
  color: string; // hex
}

export interface CustomAttribute {
  key: string;
  value: string;
}

export interface ColumnDef {
  id: ColumnId;
  label: string;
}

export interface Project {
  id: string;
  name: string;
  color: string; // hex — used in Global Overview badge
  columns: ColumnDef[];
  tags: Tag[];
  createdAt: string;
  updatedAt: string;
}

export interface Card {
  id: string;
  projectId: string;
  columnId: ColumnId;
  title: string;
  description: string;
  position: number;
  tags: Tag[];
  attributes: CustomAttribute[];
  createdAt: string;
  updatedAt: string;
}

export const DEFAULT_COLUMNS: ColumnDef[] = [
  { id: 'backlog',     label: 'Backlog' },
  { id: 'todo',        label: 'To-Do' },
  { id: 'in-progress', label: 'In Progress' },
  { id: 'completed',   label: 'Completed' },
];

export const TAG_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#14b8a6', '#3b82f6', '#6366f1', '#a855f7',
  '#ec4899', '#64748b', '#0ea5e9', '#84cc16',
];
