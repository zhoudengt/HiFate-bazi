import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useMemo } from 'react';
import { SCENE_IMAGES } from '../../utils/assets';
import { MATERIAL_LEVELS } from '../../utils/constants';
import { HOME_SCENE_HOTSPOTS, HOME_SCENE_TITLE_LAYOUT } from '../../utils/homeSceneLayout';
import { useGameStore } from '../../stores/useGameStore';
import { PAGE_BELOW_HUD } from '../../utils/hudLayout';
import { UI_COPY } from '../../utils/uiCopy';

type EntryDef = (typeof UI_COPY.home.entries)[number];

function resolveMaterialLevel(
  entry: EntryDef,
  buildings: { code: string; level: number }[],
  fallback: number,
  treeLevel: number,
) {
  if (entry.path === '/tree') return treeLevel;
  if ('buildingCode' in entry && entry.buildingCode) {
    const b = buildings.find((x) => x.code === entry.buildingCode);
    if (b) return b.level;
  }
  return fallback;
}

function materialLabel(level: number) {
  const tier = MATERIAL_LEVELS[level as keyof typeof MATERIAL_LEVELS];
  return tier ? `${tier} · ${level}阶` : UI_COPY.home.materialTierUnknown(level);
}

const showHotspotDebug = false;

export default function HomePage() {
  const navigate = useNavigate();
  const buildings = useGameStore((s) => s.buildings);
  const playerLevel = useGameStore((s) => s.level);
  const treeLevel = useGameStore((s) => s.treeLevel);

  const levelByPath = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of UI_COPY.home.entries) {
      m.set(e.path, resolveMaterialLevel(e, buildings, playerLevel, treeLevel));
    }
    return m;
  }, [buildings, playerLevel, treeLevel]);

  const entryByPath = useMemo(() => {
    const m = new Map<string, EntryDef>();
    for (const e of UI_COPY.home.entries) m.set(e.path, e);
    return m;
  }, []);

  return (
    <div className="relative flex min-h-[100dvh] w-full flex-col bg-ink">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-black/70 via-black/25 to-transparent"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/75 via-black/30 to-transparent"
        aria-hidden
      />

      <div
        className={`relative z-10 flex min-h-0 flex-1 flex-col items-center justify-center px-2 pb-[max(1rem,env(safe-area-inset-bottom))] ${PAGE_BELOW_HUD}`}
      >
        <div className="relative w-full max-w-lg shrink-0">
          <img
            src={SCENE_IMAGES.palaceSceneV2}
            alt=""
            className="block h-auto w-full max-h-[min(78dvh,calc(100dvh-var(--page-top)-5rem))] object-contain object-center"
            draggable={false}
          />
          <div className="pointer-events-none absolute inset-0">
            <div
              className="pointer-events-none absolute z-[1] text-center"
              style={{
                top: HOME_SCENE_TITLE_LAYOUT.top,
                left: HOME_SCENE_TITLE_LAYOUT.left,
                transform: HOME_SCENE_TITLE_LAYOUT.transform,
              }}
            >
              <span className="inline-block font-display text-xl font-bold tracking-[0.35em] text-black drop-shadow-[0_0_2px_rgba(255,255,255,0.95),0_1px_3px_rgba(255,255,255,0.7)] home-scene-title-float sm:text-2xl">
                {UI_COPY.home.title}
              </span>
            </div>

            {HOME_SCENE_HOTSPOTS.map((spot) => {
              const entry = entryByPath.get(spot.path);
              const level = levelByPath.get(spot.path) ?? playerLevel;
              if (!entry) return null;
              const { hit, label } = spot;
              const aria = `${entry.name}，${materialLabel(level)}`;
              return (
                <div key={spot.path}>
                  <motion.button
                    type="button"
                    onClick={() => navigate(entry.path)}
                    className={`absolute z-[2] cursor-pointer rounded-md border-0 bg-transparent p-0 transition active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-gold/80 ${
                      showHotspotDebug ? 'bg-red-500/25 ring-1 ring-red-400/60' : ''
                    }`}
                    style={{
                      top: hit.top,
                      left: hit.left,
                      width: hit.width,
                      height: hit.height,
                      pointerEvents: 'auto',
                    }}
                    aria-label={aria}
                  />
                  <div
                    className="pointer-events-none absolute z-[3] flex max-w-[26%] flex-col items-center text-center"
                    style={{
                      top: label.top,
                      left: label.left,
                      transform: label.transform,
                    }}
                  >
                    <span className="flex max-w-full flex-col items-center home-scene-label-float">
                      <span className="font-display text-sm font-bold leading-tight text-black drop-shadow-[0_0_2px_rgba(255,255,255,0.95),0_1px_3px_rgba(255,255,255,0.7)] sm:text-base">
                        {entry.name}
                      </span>
                      <span className="mt-1 rounded-full border border-ink/20 bg-white/85 px-2 py-0.5 font-body text-[10px] text-ink shadow-sm backdrop-blur-[2px] sm:text-[11px]">
                        {materialLabel(level)}
                      </span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
