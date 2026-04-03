import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

export default function BoothPage() {
  return (
    <PageContainer className="flex min-h-[60vh] flex-col items-center justify-center bg-marble/90 pb-24 ">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-md px-4 text-center"
      >
        <h1 className="font-display text-3xl tracking-widest text-ink">占桌</h1>
        <p className="mt-6 font-body text-sm leading-relaxed text-ink/75">
          在此摆设你的命理摊位，与同道交流卦象与心得。未来将支持展示擅长领域、接单与礼物互动。
        </p>
        <motion.div
          className="mt-10 flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-gold/50 bg-cream/80 px-6 py-10"
          initial={{ scale: 0.96 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.15 }}
        >
          <svg className="h-12 w-12 text-gold/80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
          <p className="font-display text-xl text-gold">敬请期待</p>
          <p className="font-body text-xs text-ink/55">功能筹备中</p>
        </motion.div>
      </motion.div>
    </PageContainer>
  );
}
