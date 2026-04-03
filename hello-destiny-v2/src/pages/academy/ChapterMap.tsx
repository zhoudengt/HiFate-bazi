import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import AcademyLayout from '../../components/layout/AcademyLayout';
import { learningApi, type LearningChapter } from '../../api/learning';
import { getSceneBg } from '../../utils/assets';

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring' as const, stiffness: 280, damping: 26 },
  },
};

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

export default function ChapterMap() {
  const navigate = useNavigate();
  const [chapters, setChapters] = useState<LearningChapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await learningApi.chapters();
      if (res.data.code === 0 && res.data.data?.chapters) {
        setChapters(res.data.data.chapters);
      } else {
        setErr(res.data.message || '加载失败');
      }
    } catch {
      setErr('网络异常，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AcademyLayout
      title="学堂"
      titleCenter
      showBack={false}
      loading={loading}
      loadingText="载入章节…"
      error={err}
    >
      <motion.div
        className="mx-auto flex max-w-lg flex-row flex-wrap items-end justify-center gap-3 px-2 sm:gap-5"
        variants={container}
        initial="hidden"
        animate="visible"
      >
        {chapters.map((ch, idx) => {
          const total = ch.sections_count || 1;
          const done = ch.completed_stages ?? 0;
          const progressLabel = `${done}/${total}`;
          const mid = idx === Math.min(chapters.length - 1, 1);
          const bgUrl = getSceneBg(ch.cover);
          return (
            <motion.button
              key={ch.id}
              type="button"
              variants={item}
              disabled={!ch.unlocked}
              onClick={() => ch.unlocked && navigate(`/academy/chapter/${ch.id}`)}
              className={`relative flex w-[30%] max-w-[118px] flex-col items-center sm:max-w-[132px] ${
                ch.unlocked ? 'cursor-pointer active:scale-[0.98]' : 'cursor-not-allowed opacity-70'
              }`}
            >
              <div
                className={`relative w-full overflow-hidden rounded-t-lg border-2 border-[#c9a227]/60 shadow-[0_16px_40px_rgba(0,0,0,0.55)] ${
                  mid ? 'min-h-[280px] sm:min-h-[300px]' : 'min-h-[248px] sm:min-h-[268px]'
                }`}
                style={{
                  boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.08), 0 12px 32px rgba(0,0,0,0.6)',
                }}
              >
                <img
                  src={bgUrl}
                  alt=""
                  className="absolute inset-0 h-full w-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/40 to-black/65" />
                <div className="relative flex h-full min-h-[inherit]">
                  <div className="min-w-0 flex-1" aria-hidden />
                  <div className="relative z-10 flex w-[44%] flex-col items-center border-l border-[#b8963e]/40 bg-gradient-to-l from-[#f2ebe0]/96 to-[#ebe3d4]/88 px-1 pb-3 pt-4 shadow-[-4px_0_12px_rgba(0,0,0,0.15)]">
                    <p
                      className="flex-1 font-display text-[11px] leading-relaxed tracking-widest text-[#1a1510] sm:text-xs"
                      style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}
                    >
                      {ch.name}
                    </p>
                    <p className="mt-2 shrink-0 font-body text-[10px] font-medium text-[#7a5c1e]">
                      {progressLabel}
                    </p>
                  </div>
                </div>
                {!ch.unlocked ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                    <LockIcon className="h-10 w-10 text-[#c9a227]/90" />
                  </div>
                ) : null}
              </div>
              <div className="mt-1 h-2 w-[85%] rounded-full bg-black/50 ring-1 ring-[#c9a227]/30">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#8b6914] to-[#d4af6a]"
                  style={{ width: `${Math.min(100, ch.completed_pct)}%` }}
                />
              </div>
            </motion.button>
          );
        })}
      </motion.div>
    </AcademyLayout>
  );
}
