import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import AcademyLayout from '../../components/layout/AcademyLayout';
import { learningApi, type QuizQuestion } from '../../api/learning';
import type { GameState } from '../../api/game';
import { useGameStore } from '../../stores/useGameStore';
import { UI_COPY } from '../../utils/uiCopy';

export default function QuizPage() {
  const { id } = useParams();
  const stageSn = id ? parseInt(id, 10) : NaN;
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [battlefield, setBattlefield] = useState(201);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [quizLoading, setQuizLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [finished, setFinished] = useState(false);
  const [resultScore, setResultScore] = useState<number | null>(null);
  const [rewardsText, setRewardsText] = useState<string | null>(null);
  const submitOnce = useRef(false);

  const loadQuiz = useCallback(async () => {
    if (!Number.isFinite(stageSn)) {
      setLoadErr('无效关卡');
      setQuizLoading(false);
      return;
    }
    setLoadErr(null);
    setQuizLoading(true);
    try {
      const res = await learningApi.stageQuiz(stageSn);
      if (res.data.code === 0 && res.data.data?.questions?.length) {
        setQuestions(res.data.data.questions);
        const bf = res.data.data.battlefield;
        setBattlefield(typeof bf === 'number' ? bf : 201);
      } else {
        setLoadErr(res.data.message || '暂无测验');
      }
    } catch {
      setLoadErr('网络异常');
    } finally {
      setQuizLoading(false);
    }
  }, [stageSn]);

  useEffect(() => {
    setStep(0);
    setSelected(null);
    setAnswers([]);
    setFinished(false);
    setResultScore(null);
    setRewardsText(null);
    submitOnce.current = false;
    void loadQuiz();
  }, [loadQuiz, stageSn]);

  const current = questions[step];
  const total = questions.length;

  const progressLabel = useMemo(() => `问题 ${step + 1}/${total}`, [step, total]);

  const onConfirm = () => {
    if (selected === null || !current || finished) return;
    const nextAnswers = [...answers, selected];
    if (step + 1 >= total) {
      if (submitOnce.current) return;
      submitOnce.current = true;
      void learningApi
        .completeStage(stageSn, nextAnswers)
        .then((res) => {
          const d = res.data;
          if (d.code === 0 && d.data?.ok) {
            setFinished(true);
            if (typeof d.data.score === 'number') setResultScore(d.data.score);
            const st = (d.data as { state?: GameState }).state;
            if (st) useGameStore.getState().applyGameState(st);
            if (d.data.already_completed) {
              setRewardsText('本关已完成过');
            } else {
              const r = d.data.rewards;
              if (r) {
                const parts: string[] = [];
                if (r.destiny_points) parts.push(`命运点 +${r.destiny_points}`);
                if (r.xp) parts.push(`经验 +${r.xp}`);
                if (r.drops?.length) {
                  parts.push(
                    r.drops.map((x) => `道具 ${x.item_id} ×${x.quantity}`).join(' · '),
                  );
                }
                setRewardsText(parts.length ? parts.join(' · ') : '已领取奖励');
              }
            }
          } else {
            submitOnce.current = false;
            setLoadErr(d.message || '提交失败');
          }
        })
        .catch(() => {
          submitOnce.current = false;
          setLoadErr('提交失败');
        });
      return;
    }
    setAnswers(nextAnswers);
    setStep((s) => s + 1);
    setSelected(null);
  };

  const subtitle =
    Number.isFinite(stageSn) ? `关卡 ${stageSn}` : '关卡 —';

  return (
    <AcademyLayout
      bgCode={battlefield}
      title="测验"
      subtitle={subtitle}
      error={loadErr}
      showBack
      onBack={() => navigate(-1)}
    >
      {quizLoading ? (
        <p className="text-center font-body text-[#e8dcc8]/80">加载题目…</p>
      ) : null}

      {!quizLoading && !loadErr && questions.length === 0 && !finished ? (
        <p className="text-center font-body text-[#e8dcc8]/70">暂无题目</p>
      ) : null}

      <AnimatePresence mode="wait">
        {!finished && current ? (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.2 }}
          >
            <p className="mb-4 text-center font-body text-[#d4af6a]">{progressLabel}</p>
            <div className="mx-auto max-w-lg rounded-2xl border border-[#c9a227]/40 bg-[#fdfaf5]/92 p-5 shadow-md backdrop-blur-sm">
              <p className="text-center font-display text-lg leading-relaxed text-ink">{current.text}</p>
            </div>
            <div className="mx-auto mt-6 grid max-w-lg gap-3">
              {current.options.map((opt, idx) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setSelected(idx)}
                  className={`rounded-xl border-2 px-4 py-3 text-left font-body transition ${
                    selected === idx
                      ? 'border-[#c9a227] bg-[#fdfaf5] shadow-[0_0_0_2px_rgba(200,164,92,0.35)]'
                      : 'border-ink/15 bg-[#fdfaf5]/90 hover:border-[#c9a227]/50'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
            <div className="mx-auto mt-8 max-w-lg">
              <motion.button
                type="button"
                whileTap={{ scale: 0.98 }}
                disabled={selected === null}
                onClick={onConfirm}
                className="w-full rounded-2xl border-2 border-[#c9a227] bg-gradient-to-r from-[#d4af6a]/95 to-[#8b6914]/90 py-3.5 font-display text-lg text-ink disabled:opacity-40"
              >
                确认选择
              </motion.button>
            </div>
          </motion.div>
        ) : null}
        {finished ? (
          <motion.div
            key="result"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mx-auto max-w-lg text-center"
          >
            <div className="rounded-2xl border-2 border-[#c9a227] bg-gradient-to-b from-[#fdfaf5] to-[#f5ecd8] p-8 shadow-xl">
              <p className="font-display text-2xl text-ink">测验完成</p>
              {resultScore !== null ? (
                <p className="mt-4 font-body text-ink/80">
                  答对 <span className="font-display text-3xl text-[#b8860b]">{resultScore}</span> / {total}
                </p>
              ) : null}
              {rewardsText ? <p className="mt-2 font-body text-sm text-[#2d6a4f]">{rewardsText}</p> : null}
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate(`/academy/chapter/${Math.floor((stageSn - 10000) / 100)}`)}
              className="mt-8 w-full rounded-2xl border border-ink/25 bg-ink py-3 font-display text-[#f5ecd8]"
            >
              {UI_COPY.academy.quizBackButton}
            </motion.button>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </AcademyLayout>
  );
}
