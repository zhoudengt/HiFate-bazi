import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import AcademyLayout from '../../components/layout/AcademyLayout';
import { learningApi, type StageDetail } from '../../api/learning';
import { UI_COPY } from '../../utils/uiCopy';

const VARIANT_SCENES: Record<number, { title: string; subtitle: string; accent: string }> = {
  0: { title: '寻道', subtitle: '落笔问易 · 静心', accent: 'from-indigo-950/85 to-slate-950/80' },
  1: { title: '问道', subtitle: '师友论理 · 明象', accent: 'from-amber-950/80 to-stone-950/75' },
  2: { title: '悟道', subtitle: '独坐观心 · 精进', accent: 'from-emerald-950/80 to-slate-950/80' },
  3: { title: '践道', subtitle: '知行合一 · 笃行', accent: 'from-rose-950/75 to-stone-950/80' },
};

export default function LessonPage() {
  const { id } = useParams();
  const stageSn = id ? parseInt(id, 10) : NaN;
  const navigate = useNavigate();
  const [detail, setDetail] = useState<StageDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(stageSn)) {
      setErr('无效关卡');
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const res = await learningApi.stageDetail(stageSn);
      if (res.data.code === 0 && res.data.data) {
        setDetail(res.data.data);
      } else {
        setErr(res.data.message || '加载失败');
      }
    } catch {
      setErr('网络异常');
    } finally {
      setLoading(false);
    }
  }, [stageSn]);

  useEffect(() => {
    void load();
  }, [load]);

  const v = detail?.experience_variant ?? 0;
  const scene = VARIANT_SCENES[v % 4] ?? VARIANT_SCENES[0];
  const label = detail?.experience_variant_label ?? scene.title;

  const bgCode = Number.isFinite(stageSn) ? (detail?.stage.battlefield ?? 201) : undefined;

  return (
    <AcademyLayout
      bgCode={bgCode}
      title={detail?.stage.name ?? '功课'}
      loading={loading}
      error={err}
      showBack
      onBack={() => navigate(-1)}
    >
      {detail ? (
        <>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mx-auto mb-6 max-w-lg rounded-2xl border border-[#c9a227]/40 bg-gradient-to-br p-5 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-sm ${scene.accent}`}
          >
            <p className="font-display text-xl text-[#fdf8f0] drop-shadow">{label}</p>
            <p className="mt-1 font-body text-sm text-[#f0e6d8]/90">{scene.subtitle}</p>
          </motion.div>

          {detail.start_dialogue?.length ? (
            <div className="mx-auto mb-4 max-w-lg space-y-2 rounded-xl border border-[#c9a227]/30 bg-[#fdfaf5]/92 p-3 shadow-md backdrop-blur-sm">
              <p className="font-body text-xs text-ink/50">开场剧情</p>
              {detail.start_dialogue.map((line) => (
                <p key={line.seq} className="font-body text-sm text-ink/85">
                  <span className="text-bronze">{line.speaker}：</span>
                  {line.content}
                </p>
              ))}
            </div>
          ) : null}

          <motion.article
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto max-w-lg rounded-xl border border-[#c9a227]/35 bg-[#fdfaf5]/90 p-4 shadow-lg backdrop-blur-sm"
          >
            <p className="font-display text-lg text-ink">学习内容</p>
            <p className="mt-3 whitespace-pre-wrap font-body text-sm leading-relaxed text-ink/85">
              {detail.lesson_body}
            </p>
          </motion.article>

          {detail.end_dialogue?.length ? (
            <div className="mx-auto mt-4 max-w-lg space-y-2 rounded-xl border border-[#c9a227]/30 bg-[#fdfaf5]/92 p-3 shadow-md backdrop-blur-sm">
              <p className="font-body text-xs text-ink/50">收场剧情</p>
              {detail.end_dialogue.map((line) => (
                <p key={line.seq} className="font-body text-sm text-ink/85">
                  <span className="text-bronze">{line.speaker}：</span>
                  {line.content}
                </p>
              ))}
            </div>
          ) : null}

          <motion.div
            className="fixed bottom-[max(5.5rem,env(safe-area-inset-bottom))] left-0 right-0 z-40 flex justify-center px-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <button
              type="button"
              onClick={() => navigate(`/academy/quiz/${stageSn}`)}
              className="w-full max-w-md rounded-2xl border-2 border-[#c9a227] bg-gradient-to-r from-[#3d3428] to-[#1a1512] py-3.5 font-display text-lg text-[#f5ecd8] shadow-[0_8px_24px_rgba(0,0,0,0.4)]"
            >
              {UI_COPY.academy.lessonCompleteButton}
            </button>
          </motion.div>
        </>
      ) : null}
    </AcademyLayout>
  );
}
