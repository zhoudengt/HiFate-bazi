export const SCENE_IMAGES = {
  caishen: '/assets/scenes/caishen.png',
  ganqing: '/assets/scenes/ganqing.png',
  shiye: '/assets/scenes/shiye.png',
  palace3d: '/assets/scenes/palace-3d.png',
  palaceFlat: '/assets/scenes/palace-flat.png',
  /** 元辰宫主场景 2.0（?v= 用于换图后绕过浏览器缓存） */
  palaceSceneV2: '/assets/scenes/yuanchen-palace-scene.jpg?v=2',
  /** 学堂关卡地图（与 v2_xuetang_chapters.cover_scene / levels.battlefield 一致） */
  battlefield201: '/assets/scenes/201.png?v=1',
  battlefield202: '/assets/scenes/202.png?v=1',
} as const;

const BATTLEFIELD_BG: Record<string, string> = {
  '201': SCENE_IMAGES.battlefield201,
  '202': SCENE_IMAGES.battlefield202,
};

/** 将数据库 battlefield / cover_scene（201、202）转为静态背景图 URL */
export function getSceneBg(code: string | number | null | undefined): string {
  const key = code == null ? '201' : String(code);
  return BATTLEFIELD_BG[key] ?? BATTLEFIELD_BG['201'];
}

export const UI_IMAGES = {
  appIcon: '/assets/ui/app-icon.png',
} as const;
