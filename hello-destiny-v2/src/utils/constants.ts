import { UI_COPY } from './uiCopy';

export const API_BASE = '/api/v2';

/** 与底部 TabBar、UI_COPY.nav.tabs 路径一致 */
export const TABS = [
  { key: 'home', label: UI_COPY.nav.tabs[0].label, path: UI_COPY.nav.tabs[0].path, icon: 'palace' },
  { key: 'quest', label: UI_COPY.nav.tabs[1].label, path: UI_COPY.nav.tabs[1].path, icon: 'quest' },
  { key: 'academy', label: UI_COPY.nav.tabs[2].label, path: UI_COPY.nav.tabs[2].path, icon: 'academy' },
  { key: 'destiny', label: UI_COPY.nav.tabs[3].label, path: UI_COPY.nav.tabs[3].path, icon: 'destiny' },
  { key: 'profile', label: UI_COPY.nav.tabs[4].label, path: UI_COPY.nav.tabs[4].path, icon: 'profile' },
] as const;

export const BUILDING_CODES = [
  'caishen', 'ganqing', 'shiye',
  'exchange', 'prayer', 'tree',
  'quest', 'academy',
] as const;

export const LIUYAO_CATEGORIES = [
  { key: 'wealth', label: '求财' },
  { key: 'love', label: '姻缘' },
  { key: 'career', label: '事业' },
  { key: 'health', label: '健康' },
  { key: 'general', label: '综合' },
] as const;

export const MATERIAL_LEVELS: Record<number, string> = {
  1: '汉白玉',
  2: '碧玉',
  3: '青铜',
};
