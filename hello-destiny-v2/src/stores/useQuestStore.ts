import { create } from 'zustand';
import type { QuestOverview } from '../api/quest';
import { questApi } from '../api/quest';

interface QuestState extends QuestOverview {
  loading: boolean;
  fetchOverview: () => Promise<void>;
}

export const useQuestStore = create<QuestState>((set) => ({
  daily: [],
  daily_boxes: [],
  weekly_boxes: [],
  daily_activity: 0,
  weekly_activity: 0,
  main: [],
  loading: false,

  fetchOverview: async () => {
    set({ loading: true });
    try {
      const res = await questApi.overview();
      if (res.data.code === 0) {
        set({ ...res.data.data });
      }
    } catch {
      /* API not ready */
    } finally {
      set({ loading: false });
    }
  },
}));
