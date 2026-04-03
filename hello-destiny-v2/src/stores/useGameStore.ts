import { create } from 'zustand';
import type { Building, GameState } from '../api/game';
import { gameApi } from '../api/game';

interface GameStateShape {
  level: number;
  xp: number;
  xpToNext: number;
  xpProgressRatio: number;
  destinyPoints: number;
  treeLevel: number;
  treeWaterToday: boolean;
  buildings: Building[];
  loading: boolean;
  refresh: () => Promise<void>;
  applyGameState: (d: GameState | null | undefined) => void;
}

function mapState(d: GameState): Pick<
  GameStateShape,
  | 'level'
  | 'xp'
  | 'xpToNext'
  | 'xpProgressRatio'
  | 'destinyPoints'
  | 'treeLevel'
  | 'treeWaterToday'
  | 'buildings'
> {
  return {
    level: d.level,
    xp: d.xp,
    xpToNext: d.xp_to_next,
    xpProgressRatio: typeof d.xp_progress_ratio === 'number' ? d.xp_progress_ratio : 0,
    destinyPoints: d.destiny_points,
    treeLevel: d.tree_level,
    treeWaterToday: d.tree_water_today,
    buildings: d.buildings ?? [],
  };
}

export const useGameStore = create<GameStateShape>((set) => ({
  level: 1,
  xp: 0,
  xpToNext: 100,
  xpProgressRatio: 0,
  destinyPoints: 0,
  treeLevel: 1,
  treeWaterToday: false,
  buildings: [],
  loading: false,

  applyGameState: (d) => {
    if (!d) return;
    set(mapState(d));
  },

  refresh: async () => {
    set({ loading: true });
    try {
      const res = await gameApi.getState();
      const payload = res.data;
      if (payload.code === 0 && payload.data) {
        set(mapState(payload.data));
      }
    } catch {
      /* 离线或表未迁移时保留本地默认值 */
    } finally {
      set({ loading: false });
    }
  },
}));
