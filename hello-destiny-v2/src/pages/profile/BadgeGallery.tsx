import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

const BADGES = [
  { id: '1', name: '初入道门', earned: true },
  { id: '2', name: '首次起卦', earned: true },
  { id: '3', name: '学习达人', earned: true },
  { id: '4', name: '连续签到7天', earned: true },
  { id: '5', name: '未解锁', earned: false },
  { id: '6', name: '未解锁', earned: false },
  { id: '7', name: '未解锁', earned: false },
  { id: '8', name: '未解锁', earned: false },
  { id: '9', name: '未解锁', earned: false },
  { id: '10', name: '未解锁', earned: false },
  { id: '11', name: '未解锁', earned: false },
  { id: '12', name: '未解锁', earned: false },
];

export default function BadgeGallery() {
  return (
    <PageContainer className="bg-cream pb-24 ">
      <motion.h1
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 text-center font-display text-2xl tracking-widest text-ink"
      >
        勋章图鉴
      </motion.h1>

      <motion.div
        className="mx-auto grid max-w-md grid-cols-4 gap-3"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.04 } },
        }}
      >
        {BADGES.map((b) => (
          <motion.div
            key={b.id}
            variants={{
              hidden: { opacity: 0, scale: 0.9 },
              visible: { opacity: 1, scale: 1 },
            }}
            className={`flex aspect-square flex-col items-center justify-center rounded-xl border-2 p-2 text-center shadow-sm ${
              b.earned
                ? 'border-gold bg-marble'
                : 'border-ink/10 bg-marble/50 grayscale'
            }`}
          >
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-full ${
                b.earned ? 'bg-gold/25 text-gold' : 'bg-ink/10 text-ink/30'
              }`}
            >
              {b.earned ? (
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                  <path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7L12 17.8 5.7 21l2.3-7-6-4.6h7.6L12 2z" />
                </svg>
              ) : (
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="5" y="11" width="14" height="10" rx="2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                </svg>
              )}
            </div>
            <p className="mt-2 font-body text-[10px] leading-tight text-ink/80">{b.name}</p>
          </motion.div>
        ))}
      </motion.div>
    </PageContainer>
  );
}
