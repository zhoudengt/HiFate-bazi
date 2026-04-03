/**
 * 元辰宫主场景：热区与浮动标签坐标（相对「与底图等尺寸的覆盖层」百分比）。
 * 三行 × 左右各一 + 中央生命之树，热区收窄在两侧窄列。
 *
 * 与 UI_COPY.home.entries 顺序一一对应：
 * - 上行左：兑换殿 | 上行右：事业殿
 * - 中行左：学堂   | 中行右：任务
 * - 中央：生命之树
 * - 下行左：感情殿 | 下行右：财神殿
 */

export type PctBox = {
  top: string;
  left: string;
  width: string;
  height: string;
};

export type HomeSceneHotspotLayout = {
  path: string;
  hit: PctBox;
  label: { top: string; left: string; transform?: string };
};

export const HOME_SCENE_TITLE_LAYOUT = {
  top: '2.5%',
  left: '50%',
  transform: 'translateX(-50%)',
} as const;

const SIDE_W = '24%';
const LEFT_X = '6%';
const RIGHT_X = '70%';
const CENTER_X = '33%';
const CENTER_W = '34%';

export const HOME_SCENE_HOTSPOTS: HomeSceneHotspotLayout[] = [
  // 上行左：兑换殿
  {
    path: '/exchange',
    hit: { top: '15%', left: LEFT_X, width: SIDE_W, height: '19%' },
    label: { top: '21%', left: '18%', transform: 'translateX(-50%)' },
  },
  // 上行右：事业殿
  {
    path: '/palace/shiye',
    hit: { top: '15%', left: RIGHT_X, width: SIDE_W, height: '19%' },
    label: { top: '21%', left: '82%', transform: 'translateX(-50%)' },
  },
  // 中行左：学堂（缩短高度、略上移，避免压到下行侧殿）
  {
    path: '/academy',
    hit: { top: '34%', left: LEFT_X, width: SIDE_W, height: '14%' },
    label: { top: '40%', left: '18%', transform: 'translateX(-50%)' },
  },
  // 中行右：任务（与学堂对称）
  {
    path: '/quest',
    hit: { top: '34%', left: RIGHT_X, width: SIDE_W, height: '14%' },
    label: { top: '40%', left: '82%', transform: 'translateX(-50%)' },
  },
  // 中央：生命之树（高度缩短，避免遮挡下行热区）
  {
    path: '/tree',
    hit: { top: '40%', left: CENTER_X, width: CENTER_W, height: '16%' },
    label: { top: '45%', left: '50%', transform: 'translateX(-50%)' },
  },
  // 下行左：感情殿
  {
    path: '/palace/ganqing',
    hit: { top: '50%', left: LEFT_X, width: SIDE_W, height: '21%' },
    label: { top: '57%', left: '18%', transform: 'translateX(-50%)' },
  },
  // 下行右：财神殿
  {
    path: '/palace/caishen',
    hit: { top: '50%', left: RIGHT_X, width: SIDE_W, height: '21%' },
    label: { top: '57%', left: '82%', transform: 'translateX(-50%)' },
  },
];
