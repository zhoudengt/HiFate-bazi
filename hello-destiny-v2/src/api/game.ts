import { api } from './client';

export interface GameState {
  level: number;
  xp: number;
  xp_to_next: number;
  /** 当前等级段内进度 0~1，由服务端计算 */
  xp_progress_ratio?: number;
  destiny_points: number;
  tree_level: number;
  tree_water_today: boolean;
  buildings: Building[];
}

export interface Building {
  code: string;
  name: string;
  unlocked: boolean;
  level: number;
}

export interface XpAddPayload {
  amount: number;
  source: string;
  source_detail?: string;
}

export interface PointsAddPayload {
  amount: number;
  source: string;
  source_detail?: string;
}

/** POST /game/tree/water */
export interface WaterTreeData {
  tree_level?: number;
  reward?: { xp?: number; destiny_points?: number };
  tree_water_today?: boolean;
  state?: GameState | null;
}

export const gameApi = {
  getState: () => api.get<{ code: number; message?: string; data: GameState }>('/game/state'),
  waterTree: () =>
    api.post<{ code: number; message?: string; data: WaterTreeData | null }>('/game/tree/water'),
  addXp: (body: XpAddPayload) =>
    api.post<{
      code: number;
      message?: string;
      data: { xp_result: Record<string, unknown>; state: GameState | null };
    }>('/game/xp/add', body),
  addPoints: (body: PointsAddPayload) =>
    api.post<{
      code: number;
      message?: string;
      data: { points_result: Record<string, unknown>; state: GameState | null };
    }>('/game/points/add', body),
};
