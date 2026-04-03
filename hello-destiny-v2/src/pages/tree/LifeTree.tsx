import { useState } from 'react';
import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';
import { gameApi } from '../../api/game';
import { useGameStore } from '../../stores/useGameStore';

function TreeSvg() {
  return (
    <svg viewBox="0 0 200 220" className="h-56 w-48 text-jade" fill="none" aria-hidden>
      <path
        d="M100 200 L100 120"
        stroke="url(#trunk)"
        strokeWidth="14"
        strokeLinecap="round"
      />
      <defs>
        <linearGradient id="trunk" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#5a8a72" />
          <stop offset="100%" stopColor="#2d5a4c" />
        </linearGradient>
        <radialGradient id="leaf" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#c8a45c" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#2d5a4c" stopOpacity="0.95" />
        </radialGradient>
      </defs>
      <circle cx="100" cy="75" r="58" fill="url(#leaf)" />
      <circle cx="70" cy="95" r="32" fill="#3d7a62" opacity="0.9" />
      <circle cx="130" cy="95" r="32" fill="#3d7a62" opacity="0.9" />
      <circle cx="100" cy="45" r="28" fill="#c8a45c" opacity="0.35" />
      <ellipse cx="100" cy="205" rx="40" ry="8" fill="rgba(26,60,52,0.15)" />
    </svg>
  );
}

export default function LifeTree() {
  const level = useGameStore((s) => s.treeLevel);
  const watered = useGameStore((s) => s.treeWaterToday);
  const xp = useGameStore((s) => s.xp);
  const xpToNext = useGameStore((s) => s.xpToNext);
  const refresh = useGameStore((s) => s.refresh);
  const [watering, setWatering] = useState(false);
  const pct = xpToNext > 0 ? Math.min(100, Math.round((xp / xpToNext) * 100)) : 0;

  const onWater = async () => {
    if (watered || watering) return;
    setWatering(true);
    try {
      const res = await gameApi.waterTree();
      const body = res.data;
      if (body.code === 0 && body.data?.state) {
        useGameStore.getState().applyGameState(body.data.state);
      } else if (body.code === 4) {
        await refresh();
      } else {
        await refresh();
      }
    } catch {
      await refresh().catch(() => {});
    } finally {
      setWatering(false);
    }
  };

  return (
    <PageContainer className="bg-gradient-to-b from-cream via-marble/80 to-jade/20 pb-28 ">
      <motion.h1
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-2 text-center font-display text-2xl tracking-widest text-ink"
      >
        生命之树
      </motion.h1>
      <p className="mb-8 text-center font-body text-sm text-ink/65">灵根滋养，气运绵长</p>

      <motion.div
        className="flex flex-col items-center"
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 22 }}
      >
        <TreeSvg />
        <p className="mt-2 font-display text-lg text-gold">灵阶 {level}</p>
      </motion.div>

      <div className="mx-auto mt-8 max-w-md rounded-2xl border border-gold/35 bg-cream p-5 shadow-md">
        <p className="font-body text-sm text-ink/70">下一级进度</p>
        <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-marble">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-jade to-gold"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6 }}
          />
        </div>
        <p className="mt-2 text-right font-body text-xs text-ink/50">
          {xp} / {xpToNext}
        </p>
        <p className="mt-4 font-body text-sm text-jade">升级预览：灵阶 {level + 1} 解锁新场景贴图</p>
      </div>

      <motion.div className="mx-auto mt-8 max-w-xs">
        <motion.button
          type="button"
          whileTap={{ scale: watered || watering ? 1 : 0.97 }}
          disabled={watered || watering}
          onClick={() => void onWater()}
          className={`w-full rounded-2xl border-2 border-gold py-3.5 font-display text-lg ${
            watered || watering ? 'cursor-not-allowed bg-marble text-ink/40' : 'bg-ink text-cream'
          }`}
        >
          {watered ? '今日已浇灌' : watering ? '浇灌中…' : '浇灌'}
        </motion.button>
      </motion.div>
    </PageContainer>
  );
}
