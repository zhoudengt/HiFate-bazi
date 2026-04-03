import { create } from 'zustand';

interface LiuyaoState {
  question: string;
  category: string;
  method: 'coin' | 'number' | 'time';
  coinResults: number[];
  castingId: number | null;
  hexagramData: unknown | null;
  aiText: string;
  setQuestion: (q: string) => void;
  setCategory: (c: string) => void;
  setMethod: (m: 'coin' | 'number' | 'time') => void;
  addCoinResult: (v: number) => void;
  resetCoins: () => void;
  setCastingId: (id: number | null) => void;
  setHexagramData: (d: unknown) => void;
  appendAiText: (t: string) => void;
  resetAiText: () => void;
  resetAll: () => void;
}

export const useLiuyaoStore = create<LiuyaoState>((set) => ({
  question: '',
  category: 'general',
  method: 'coin',
  coinResults: [],
  castingId: null,
  hexagramData: null,
  aiText: '',

  setQuestion: (q) => set({ question: q }),
  setCategory: (c) => set({ category: c }),
  setMethod: (m) => set({ method: m }),
  addCoinResult: (v) => set((s) => ({ coinResults: [...s.coinResults, v] })),
  resetCoins: () => set({ coinResults: [] }),
  setCastingId: (id) => set({ castingId: id }),
  setHexagramData: (d) => set({ hexagramData: d }),
  appendAiText: (t) => set((s) => ({ aiText: s.aiText + t })),
  resetAiText: () => set({ aiText: '' }),
  resetAll: () =>
    set({
      question: '',
      category: 'general',
      method: 'coin',
      coinResults: [],
      castingId: null,
      hexagramData: null,
      aiText: '',
    }),
}));
