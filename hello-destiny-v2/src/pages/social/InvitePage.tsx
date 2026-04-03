import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

const MILESTONES = [
  { need: 1, reward: '20 命运点数' },
  { need: 3, reward: '抉择罗盘碎片 ×1' },
  { need: 5, reward: '限定头像框' },
];

export default function InvitePage() {
  const code = 'YQ88-DESTINY';
  const invited = 2;
  const earnedPoints = 40;

  return (
    <PageContainer className="bg-gradient-to-b from-cream to-marble/90 pb-28 ">
      <motion.h1
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 text-center font-display text-2xl tracking-[0.2em] text-ink"
      >
        邀请好友
      </motion.h1>

      <motion.div
        className="mx-auto max-w-md rounded-2xl border-2 border-gold/40 bg-ink px-5 py-6 text-center shadow-xl"
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <p className="font-body text-xs tracking-widest text-cream/60">我的邀请码</p>
        <p className="mt-2 font-display text-2xl tracking-[0.35em] text-gold">{code}</p>
      </motion.div>

      <div className="mx-auto mt-8 grid max-w-md grid-cols-2 gap-4">
        <div className="rounded-2xl border border-ink/10 bg-marble p-4 text-center shadow">
          <p className="font-display text-2xl text-jade">{invited}</p>
          <p className="mt-1 font-body text-xs text-ink/60">已邀请人数</p>
        </div>
        <div className="rounded-2xl border border-ink/10 bg-marble p-4 text-center shadow">
          <p className="font-display text-2xl text-gold">{earnedPoints}</p>
          <p className="mt-1 font-body text-xs text-ink/60">已获得点数</p>
        </div>
      </div>

      <motion.button
        type="button"
        whileTap={{ scale: 0.98 }}
        className="mx-auto mt-8 flex w-full max-w-md items-center justify-center rounded-2xl border-2 border-gold bg-gradient-to-r from-gold to-bronze py-3.5 font-display text-lg text-ink shadow-lg"
      >
        分享邀请
      </motion.button>

      <div className="mx-auto mt-10 max-w-md">
        <p className="mb-3 font-display text-ink">里程碑奖励</p>
        <ul className="space-y-3">
          {MILESTONES.map((m, i) => (
            <motion.li
              key={m.need}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.05 * i }}
              className="flex items-center justify-between rounded-xl border border-gold/25 bg-cream px-4 py-3"
            >
              <span className="font-body text-sm text-ink">邀请满 {m.need} 人</span>
              <span className="font-body text-xs text-jade">{m.reward}</span>
            </motion.li>
          ))}
        </ul>
      </div>
    </PageContainer>
  );
}
