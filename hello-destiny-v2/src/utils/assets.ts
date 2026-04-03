const BASE = import.meta.env.BASE_URL;

/** Resolve a public/ asset path with the Vite base prefix (`/v2/` in prod, `/` in dev). */
export function assetUrl(path: string): string {
  const p = path.startsWith('/') ? path.slice(1) : path;
  return `${BASE}${p}`;
}

export const SCENE_IMAGES = {
  caishen: assetUrl('assets/scenes/caishen.png'),
  ganqing: assetUrl('assets/scenes/ganqing.png'),
  shiye: assetUrl('assets/scenes/shiye.png'),
  palace3d: assetUrl('assets/scenes/palace-3d.png'),
  palaceFlat: assetUrl('assets/scenes/palace-flat.png'),
  /** 元辰宫主场景 2.0（?v= 用于换图后绕过浏览器缓存） */
  palaceSceneV2: assetUrl('assets/scenes/yuanchen-palace-scene.jpg?v=2'),
  /** 学堂关卡地图（与 v2_xuetang_chapters.cover_scene / levels.battlefield 一致） */
  battlefield201: assetUrl('assets/scenes/201.png?v=1'),
  battlefield202: assetUrl('assets/scenes/202.png?v=1'),
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
  appIcon: assetUrl('assets/ui/app-icon.png'),
} as const;
