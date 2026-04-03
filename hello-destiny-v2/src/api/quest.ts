import { api } from './client';

export interface DailyQuest {
  id: number;
  name: string;
  tasktype: number;
  target: number;
  progress: number;
  completed: boolean;
  claimed: boolean;
  reward_item_id: number;
  reward_num: number;
  activity_point: number;
}

export interface BoxConfig {
  id: number;
  name: string;
  threshold: number;
  reward_item_id: number;
  reward_num: number;
  claimed: boolean;
}

export interface MainQuest {
  id: number;
  tasktype: number;
  tasktype_label: string;
  taskname: string;
  condition_value: number;
  award_item_id: number;
  award_num: number;
  completed: boolean;
  claimed: boolean;
}

export interface QuestOverview {
  daily: DailyQuest[];
  daily_boxes: BoxConfig[];
  weekly_boxes: BoxConfig[];
  daily_activity: number;
  weekly_activity: number;
  main: MainQuest[];
}

export interface ClaimResult {
  ok: boolean;
  error?: string;
  reward_item_id?: number;
  reward_num?: number;
  activity_added?: number;
  destiny_points?: number;
}

export const questApi = {
  overview: () =>
    api.get<{ code: number; data: QuestOverview }>('/quest/overview'),

  claimDaily: (quest_config_id: number) =>
    api.post<{ code: number; data: ClaimResult }>('/quest/claim-daily', { quest_config_id }),

  claimMain: (quest_id: number) =>
    api.post<{ code: number; data: ClaimResult }>('/quest/claim-main', { quest_id }),

  claimBox: (box_config_id: number) =>
    api.post<{ code: number; data: ClaimResult }>('/quest/claim-box', { box_config_id }),

  recordAction: (tasktype: number) =>
    api.post('/quest/record-action', { tasktype }),
};
