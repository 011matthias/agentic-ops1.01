import { create } from 'zustand';

interface UIState {
  activeModal: { type: 'card'; cardId: string } | null;
  openCardModal: (cardId: string) => void;
  closeModal: () => void;
  addingCard: { projectId: string; columnId: string } | null;
  setAddingCard: (v: { projectId: string; columnId: string } | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeModal: null,
  openCardModal: (cardId) => set({ activeModal: { type: 'card', cardId } }),
  closeModal: () => set({ activeModal: null }),
  addingCard: null,
  setAddingCard: (v) => set({ addingCard: v }),
}));
