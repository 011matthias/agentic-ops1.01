import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Card, ColumnDef, ColumnId, Project } from '../types/index.ts';
import { DEFAULT_COLUMNS } from '../types/index.ts';
import { api } from '../api/client.ts';

interface BoardState {
  projects: Project[];
  cards: Card[];
  activeProjectId: string | null;
  isGlobalOverview: boolean;
  serverAvailable: boolean;

  loadFromServer: () => Promise<void>;

  createProject: (name: string, color: string) => void;
  updateProject: (id: string, patch: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setActiveProject: (id: string | null) => void;
  setGlobalOverview: (v: boolean) => void;
  renameColumn: (projectId: string, columnId: ColumnId, newLabel: string) => void;

  createCard: (projectId: string, columnId: ColumnId, title: string) => void;
  updateCard: (id: string, patch: Partial<Card>) => void;
  moveCard: (cardId: string, targetColumnId: ColumnId, targetPosition: number) => void;
  deleteCard: (id: string) => void;
}

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 11)}`;
}

function now() {
  return new Date().toISOString();
}

function maxPosition(cards: Card[], projectId: string, columnId: ColumnId) {
  return cards
    .filter(c => c.projectId === projectId && c.columnId === columnId)
    .reduce((m, c) => Math.max(m, c.position), 0);
}

export const useBoardStore = create<BoardState>()(
  persist(
    (set, get) => ({
      projects: [],
      cards: [],
      activeProjectId: null,
      isGlobalOverview: false,
      serverAvailable: false,

      loadFromServer: async () => {
        try {
          const [projects, cards] = await Promise.all([
            api.projects.list(),
            api.cards.list(),
          ]);
          set({ projects, cards, serverAvailable: true });
        } catch {
          set({ serverAvailable: false });
        }
      },

      createProject: (name, color) => {
        const id = uid('proj');
        const project: Project = {
          id, name, color,
          columns:   DEFAULT_COLUMNS,
          tags:      [],
          createdAt: now(),
          updatedAt: now(),
        };
        // Client generates the ID — same ID sent to server, no race condition
        set(s => ({ projects: [...s.projects, project] }));
        api.projects.create(id, name, color).catch(() => {});
      },

      updateProject: (id, patch) => {
        set(s => ({
          projects: s.projects.map(p => p.id === id ? { ...p, ...patch, updatedAt: now() } : p),
        }));
        api.projects.update(id, patch).catch(() => {});
      },

      deleteProject: (id) => {
        set(s => ({
          projects:         s.projects.filter(p => p.id !== id),
          cards:            s.cards.filter(c => c.projectId !== id),
          activeProjectId:  s.activeProjectId === id ? null : s.activeProjectId,
          isGlobalOverview: s.activeProjectId === id ? false : s.isGlobalOverview,
        }));
        api.projects.delete(id).catch(() => {});
      },

      setActiveProject: (id) => set({ activeProjectId: id, isGlobalOverview: false }),

      setGlobalOverview: (v) => set({ isGlobalOverview: v, activeProjectId: v ? null : get().activeProjectId }),

      renameColumn: (projectId, columnId, newLabel) => {
        const project = get().projects.find(p => p.id === projectId);
        if (!project) return;
        const columns: ColumnDef[] = project.columns.map(col =>
          col.id === columnId ? { ...col, label: newLabel } : col
        );
        get().updateProject(projectId, { columns });
      },

      createCard: (projectId, columnId, title) => {
        const id = uid('card');
        const position = maxPosition(get().cards, projectId, columnId) + 1024;
        const card: Card = {
          id, projectId, columnId, title,
          description: '',
          position,
          tags:        [],
          attributes:  [],
          createdAt:   now(),
          updatedAt:   now(),
        };
        set(s => ({ cards: [...s.cards, card] }));
        api.cards.create(id, projectId, columnId, title).catch(() => {});
      },

      updateCard: (id, patch) => {
        set(s => ({
          cards: s.cards.map(c => c.id === id ? { ...c, ...patch, updatedAt: now() } : c),
        }));
        api.cards.update(id, patch).catch(() => {});
      },

      moveCard: (cardId, targetColumnId, targetPosition) => {
        set(s => ({
          cards: s.cards.map(c =>
            c.id === cardId
              ? { ...c, columnId: targetColumnId, position: targetPosition, updatedAt: now() }
              : c
          ),
        }));
        api.cards.update(cardId, { columnId: targetColumnId, position: targetPosition }).catch(() => {});
      },

      deleteCard: (id) => {
        set(s => ({ cards: s.cards.filter(c => c.id !== id) }));
        api.cards.delete(id).catch(() => {});
      },
    }),
    {
      name: 'omniboard-state',
      partialize: (s) => ({ projects: s.projects, cards: s.cards, activeProjectId: s.activeProjectId }),
    }
  )
);
