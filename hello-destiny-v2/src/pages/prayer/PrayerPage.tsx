import { useState } from 'react';
import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

export default function PrayerPage() {
  const [prayed, setPrayed] = useState(false);
  const streak = 7;

  return (
    <PageContainer className="relative flex min-h-[70vh] flex-col items-center justify-center bg-ink pb-28 ">
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          background: 'radial-gradient(ellipse at 50% 30%, rgba(200,164,92,0.35) 0%, transparent 55%)',
        }}
      />

      <motion.div
        className="relative mb-10 flex flex-col items-center"
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45 }}
      >
        <div className="relative flex h-36 w-24 items-end justify-center">
          <motion.div
            className="absolute bottom-0 h-24 w-3 rounded-full bg-gradient-to-t from-bronze via-gold to-yellow-100 shadow-[0_0_24px_rgba(200,164,92,0.85)]"
            animate={{ opacity: [0.85, 1, 0.85], scaleY: [1, 1.04, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="absolute bottom-[5.5rem] h-16 w-16 rounded-full bg-gold/25 blur-xl"
            animate={{ opacity: [0.4, 0.75, 0.4], scale: [1, 1.15, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
          />
          <svg className="relative z-10 h-20 w-14 text-gold drop-shadow-lg" viewBox="0 0 64 96" fill="currentColor" aria-hidden>
            <ellipse cx="32" cy="88" rx="18" ry="6" className="text-bronze/50" />
            <rect x="26" y="40" width="12" height="44" rx="3" className="text-bronze" />
            <ellipse cx="32" cy="38" rx="10" ry="6" />
          </svg>
        </div>
        <p className="mt-2 font-body text-xs tracking-widest text-cream/60">心香一瓣</p>
      </motion.div>

      <motion.div
        className="relative z-10 mx-auto w-full max-w-md rounded-2xl border-2 border-gold/45 bg-gradient-to-b from-marble/95 to-cream px-6 py-8 shadow-2xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <p className="text-center font-display text-xl leading-relaxed text-ink">上上签</p>
        <p className="mt-4 text-center font-body text-base leading-8 text-ink/85">风调雨顺，万事如意</p>
      </motion.div>

      <p className="relative z-10 mt-6 font-body text-sm text-gold/90">连续祈福 {streak} 天</p>

      <motion.div className="relative z-10 mt-10 w-full max-w-xs px-4">
        <motion.button
          type="button"
          whileTap={{ scale: prayed ? 1 : 0.97 }}
          disabled={prayed}
          onClick={() => setPrayed(true)}
          className={`w-full rounded-2xl border-2 border-gold py-4 font-display text-xl tracking-[0.2em] shadow-[0_8px_32px_rgba(200,164,92,0.35)] ${
            prayed
              ? 'cursor-not-allowed bg-marble/80 text-ink/45'
              : 'bg-gradient-to-r from-gold via-gold to-bronze text-ink'
          }`}
        >
          {prayed ? '已祈福' : '今日祈福'}
        </motion.button>
      </motion.div>
    </PageContainer>
  );
}
