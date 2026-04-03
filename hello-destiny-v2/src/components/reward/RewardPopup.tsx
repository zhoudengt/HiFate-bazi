import { AnimatePresence, motion } from 'framer-motion';

type RewardPopupProps = {
  open: boolean;
  rewards: { xp?: number; destiny_points?: number };
  onClose: () => void;
};

function Sparkles() {
  const seeds = [12, 28, 44, 58, 72, 86];
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl" aria-hidden>
      {seeds.map((left, i) => (
        <motion.span
          key={i}
          className="absolute bottom-1/4 h-1 w-1 rounded-full bg-gold shadow-[0_0_6px_#c8a45c]"
          style={{ left: `${left}%` }}
          initial={{ opacity: 0, y: 8, scale: 0.4 }}
          animate={{
            opacity: [0, 1, 0.4, 0],
            y: [-4, -28 - (i % 3) * 8],
            scale: [0.4, 1.1, 0.8, 0.3],
          }}
          transition={{ duration: 1.4 + (i % 4) * 0.12, repeat: Infinity, repeatDelay: 0.35 + i * 0.05 }}
        />
      ))}
    </div>
  );
}

export default function RewardPopup({ open, rewards, onClose }: RewardPopupProps) {
  const hasXp = typeof rewards.xp === 'number' && rewards.xp > 0;
  const hasDp = typeof rewards.destiny_points === 'number' && rewards.destiny_points > 0;

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[110] flex items-center justify-center p-6 font-body"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <button type="button" className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-label="关闭" onClick={onClose} />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reward-title"
            className="relative z-[1] w-full max-w-sm overflow-hidden rounded-2xl border-2 border-gold/50 bg-gradient-to-b from-ink via-jade to-ink p-6 text-center shadow-2xl"
            initial={{ scale: 0.88, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.92, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
          >
            <Sparkles />
            <h2 id="reward-title" className="relative font-display text-2xl text-gold">
              获得奖励
            </h2>
            <div className="relative mt-6 space-y-3 text-cream">
              {hasXp ? (
                <p className="text-lg">
                  经验 <span className="font-semibold text-gold">+{rewards.xp}</span>
                </p>
              ) : null}
              {hasDp ? (
                <p className="text-lg">
                  命运点数 <span className="font-semibold text-gold">+{rewards.destiny_points}</span>
                </p>
              ) : null}
              {!hasXp && !hasDp ? <p className="text-cream/80">暂无奖励</p> : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="relative mt-8 w-full rounded-xl bg-gold py-2.5 font-medium text-ink shadow-lg transition hover:brightness-105"
            >
              收下
            </button>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
