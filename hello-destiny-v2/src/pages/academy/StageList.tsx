import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import AcademyLayout from '../../components/layout/AcademyLayout';
import { learningApi, type LearningStage } from '../../api/learning';
import { getSceneBg } from '../../utils/assets';

export default function StageList() {
  const { id } = useParams();
  const chapterId = id ? parseInt(id, 10) : NaN;
  const navigate = useNavigate();
  const [title, setTitle] = useState('章节');
  const [desc, setDesc] = useState('');
  const [cover, setCover] = useState<string>('201');
  const [stages, setStages] = useState<LearningStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(chapterId)) {
      setErr('无效章节');
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const res = await learningApi.chapterStages(chapterId);
      if (res.data.code === 0 && res.data.data) {
        const ch = res.data.data.chapter;
        setTitle(ch.name);
        setDesc(ch.description || '');
        const list = res.data.data.stages;
        setStages(list);
        const cov = ch.cover ?? (list[0] ? String(list[0].battlefield) : '201');
        setCover(cov);
      } else {
        setErr(res.data.message || '加载失败');
      }
    } catch {
      setErr('网络异常');
    } finally {
      setLoading(false);
    }
  }, [chapterId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AcademyLayout
      bgCode={cover}
      title={title}
      subtitle={desc || undefined}
      loading={loading}
      loadingText="载入关卡…"
      error={err}
      showBack
      onBack={() => navigate(-1)}
    >
      <motion.div
        className="mx-auto flex max-w-lg flex-col gap-3"
        initial="hidden"
        animate="visible"
        variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}
      >
        {stages.map((s) => {
          const rowBg = getSceneBg(s.battlefield);
          return (
            <motion.button
              key={s.sn}
              type="button"
              variants={{
                hidden: { opacity: 0, y: 14 },
                visible: { opacity: 1, y: 0 },
              }}
              disabled={s.locked}
              onClick={() => {
                if (!s.locked) navigate(`/academy/lesson/${s.sn}`);
              }}
              className={`relative flex w-full min-h-[88px] overflow-hidden rounded-xl border-2 text-left shadow-lg transition ${
                s.locked
                  ? 'cursor-not-allowed border-white/15 opacity-65'
                  : 'border-[#c9a227]/45 active:scale-[0.99]'
              }`}
            >
              <div className="relative flex min-w-0 flex-1 flex-col justify-center gap-1 bg-[#1c1916]/88 px-3 py-3 backdrop-blur-[2px]">
                <span className="font-body text-xs text-[#c9a227]/95">
                  {chapterId}-{s.stage_index}
                </span>
                <span className={`font-display text-base ${s.locked ? 'text-[#8a8580]' : 'text-[#f0e6d8]'}`}>
                  {s.name}
                </span>
                <span className="font-body text-[11px] text-[#a09080]">
                  通关 +{s.reward_preview.destiny_points} 命运点 · +{s.reward_preview.xp} 经验
                </span>
              </div>
              <div className="relative w-[38%] max-w-[140px] shrink-0 border-l border-[#c9a227]/25">
                <img src={rowBg} alt="" className="absolute inset-0 h-full w-full object-cover" loading="lazy" />
                <div className="absolute inset-0 bg-gradient-to-r from-[#1c1916]/90 to-transparent" />
                <div className="relative flex h-full flex-col items-end justify-center gap-1 p-2">
                  {s.completed ? (
                    <span className="rounded-full border border-[#2d6a4f]/60 bg-[#1b4332]/75 px-2 py-0.5 font-body text-[10px] text-[#95d5b2]">
                      已完成
                    </span>
                  ) : null}
                  {s.locked ? (
                    <span className="font-body text-[10px] text-[#b0a090]">未解锁</span>
                  ) : (
                    <span className="font-body text-[10px] font-medium text-[#d4af6a]">进入</span>
                  )}
                </div>
              </div>
            </motion.button>
          );
        })}
      </motion.div>
    </AcademyLayout>
  );
}
