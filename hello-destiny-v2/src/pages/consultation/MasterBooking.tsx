import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

const MASTERS = [
  {
    id: '1',
    name: '清玄子',
    specialty: '事业财运 · 奇门择时',
    price: 199,
  },
  {
    id: '2',
    name: '若水居士',
    specialty: '感情合婚 · 八字合盘',
    price: 299,
  },
];

export default function MasterBooking() {
  return (
    <PageContainer className="bg-cream pb-28 ">
      <motion.h1
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-2 text-center font-display text-2xl text-ink"
      >
        真人大师
      </motion.h1>
      <p className="mb-8 text-center font-body text-sm text-ink/55">真人一对一，敬请期待上线</p>

      <div className="mx-auto flex max-w-md flex-col gap-4">
        {MASTERS.map((m, i) => (
          <motion.article
            key={m.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i }}
            className="flex gap-4 rounded-2xl border border-gold/30 bg-marble p-4 shadow-sm"
          >
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 border-gold/40 bg-cream">
              <svg className="h-9 w-9 text-gold/75" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                <circle cx="12" cy="9" r="4" />
                <path d="M5 21v-1a7 7 0 0 1 14 0v1" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-lg text-ink">{m.name}</h2>
              <p className="mt-1 font-body text-xs text-ink/65">{m.specialty}</p>
              <p className="mt-2 font-body text-sm text-gold">¥{m.price} / 次</p>
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.97 }}
              disabled
              className="self-center rounded-xl border border-ink/15 bg-ink/15 px-3 py-2 font-display text-sm text-ink/40"
            >
              预约
            </motion.button>
          </motion.article>
        ))}
      </div>

      <motion.div
        className="mx-auto mt-12 max-w-md rounded-2xl border border-dashed border-gold/50 bg-marble/50 px-4 py-8 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <p className="font-display text-lg text-gold">敬请期待</p>
        <p className="mt-2 font-body text-xs text-ink/50">开放预约后将在此展示档期与评价</p>
      </motion.div>
    </PageContainer>
  );
}
