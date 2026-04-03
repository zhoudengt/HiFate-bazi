import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { liuyaoApi } from '../../api/liuyao';
import { useLiuyaoStore } from '../../stores/useLiuyaoStore';

const COIN_VALUES = [2, 3, 6, 9] as const;
const VALUE_LABEL: Record<number, string> = {
  2: '少阴',
  3: '少阳',
  6: '老阴',
  9: '老阳',
};

function randomCoinValue(): number {
  return COIN_VALUES[Math.floor(Math.random() * COIN_VALUES.length)];
}

const COIN_FRONT = '/assets/coins/coin-front.png';
const COIN_BACK = '/assets/coins/coin-back.png';

/** 少阳、老阳为「阳」面，对应铜钱正面；三枚钱各自一面，由本爻数值唯一确定 */
function coinFacesForValue(v: number): [boolean, boolean, boolean] {
  switch (v) {
    case 9:
      return [true, true, true]; // 老阳：三正
    case 3:
      return [true, true, false]; // 少阳：两正一反
    case 2:
      return [true, false, false]; // 少阴：一正两反
    case 6:
      return [false, false, false]; // 老阴：三反
    default:
      return [true, true, true];
  }
}

function CoinFace({
  index,
  flipping,
  faceYang,
}: {
  index: number;
  flipping: boolean;
  faceYang: boolean;
}) {
  const delay = index * 0.06;
  if (flipping) {
    return (
      <div className="h-20 w-20 [perspective:640px]">
        <motion.div
          className="relative h-full w-full"
          style={{ transformStyle: 'preserve-3d' }}
          initial={{ rotateY: 0 }}
          animate={{ rotateY: 720 }}
          transition={{ duration: 0.7, ease: 'easeInOut', delay }}
        >
          <img
            src={COIN_FRONT}
            alt=""
            className="absolute inset-0 h-full w-full object-contain [backface-visibility:hidden]"
            style={{ transform: 'translateZ(1px)' }}
            draggable={false}
          />
          <img
            src={COIN_BACK}
            alt=""
            className="absolute inset-0 h-full w-full object-contain [backface-visibility:hidden]"
            style={{ transform: 'rotateY(180deg) translateZ(1px)' }}
            draggable={false}
          />
        </motion.div>
      </div>
    );
  }
  return (
    <div className="flex h-20 w-20 items-center justify-center">
      <img
        src={faceYang ? COIN_FRONT : COIN_BACK}
        alt=""
        className="h-full w-full object-contain drop-shadow-md"
        draggable={false}
      />
    </div>
  );
}

export default function CastingPage() {
  const navigate = useNavigate();
  const question = useLiuyaoStore((s) => s.question);
  const category = useLiuyaoStore((s) => s.category);
  const coinResults = useLiuyaoStore((s) => s.coinResults);
  const addCoinResult = useLiuyaoStore((s) => s.addCoinResult);
  const resetCoins = useLiuyaoStore((s) => s.resetCoins);
  const setCastingId = useLiuyaoStore((s) => s.setCastingId);
  const setHexagramData = useLiuyaoStore((s) => s.setHexagramData);

  const [phase, setPhase] = useState<'countdown' | 'toss' | 'flash' | 'submitting'>('countdown');
  const [countdownSecs, setCountdownSecs] = useState(3);
  const [round, setRound] = useState(1);
  const [lastValue, setLastValue] = useState<number | null>(null);
  const [flipping, setFlipping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    resetCoins();
    return () => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
    };
  }, [resetCoins]);

  useEffect(() => {
    if (phase !== 'countdown') return;
    if (countdownSecs <= 0) {
      setPhase('toss');
      return;
    }
    const t = setTimeout(() => setCountdownSecs((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, countdownSecs]);

  const finishAndNavigate = useCallback(async () => {
    setPhase('submitting');
    setError(null);
    try {
      const res = await liuyaoApi.divinate({
        question,
        method: 'coin',
        category,
        coin_results: useLiuyaoStore.getState().coinResults,
        persist: true,
      });
      const body = res.data as {
        success?: boolean;
        data?: unknown;
        casting_id?: number | null;
      };
      if (!body.success || !body.data) {
        setError('起卦失败，请稍后重试');
        setPhase('toss');
        return;
      }
      setHexagramData(body.data);
      setCastingId(body.casting_id ?? null);
      navigate('/liuyao/result/0');
    } catch (e) {
      setError(e instanceof Error ? e.message : '网络异常');
      setPhase('toss');
    }
  }, [category, navigate, question, setCastingId, setHexagramData]);

  const doToss = useCallback(() => {
    if (phase !== 'toss') return;
    if (flipping) return;
    if (!question.trim()) {
      setError('请先填写所问');
      return;
    }

    setFlipping(true);
    setError(null);

    const v = randomCoinValue();
    setLastValue(v);

    window.setTimeout(() => {
      addCoinResult(v);
      setFlipping(false);
      setPhase('flash');

      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      advanceTimer.current = setTimeout(() => {
        const nextRound = round + 1;
        if (nextRound > 6) {
          void finishAndNavigate();
          return;
        }
        setRound(nextRound);
        setLastValue(null);
        setPhase('toss');
      }, 900);
    }, 700);
  }, [
    addCoinResult,
    finishAndNavigate,
    flipping,
    phase,
    question,
    round,
  ]);

  const coinFaces: [boolean, boolean, boolean] =
    phase === 'flash' && lastValue != null
      ? coinFacesForValue(lastValue)
      : phase === 'submitting' && coinResults.length > 0
        ? coinFacesForValue(coinResults[coinResults.length - 1]!)
        : [true, true, true];

  return (
    <div
      className="relative flex min-h-full flex-col bg-cream font-body text-ink"
      style={{
        backgroundImage: `
          radial-gradient(ellipse 120% 80% at 20% 10%, rgba(26, 60, 52, 0.06) 0%, transparent 50%),
          radial-gradient(ellipse 100% 60% at 80% 90%, rgba(26, 60, 52, 0.05) 0%, transparent 45%),
          repeating-linear-gradient(0deg, transparent, transparent 24px, rgba(26, 60, 52, 0.03) 24px, rgba(26, 60, 52, 0.03) 25px)
        `,
      }}
      onClick={() => {
        if (phase === 'toss' && !flipping) doToss();
      }}
    >
      <div className="pointer-events-none absolute inset-0 opacity-[0.07] mix-blend-multiply bg-[url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22120%22%3E%3Cfilter id=%22n%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%224%22/%3E%3C/filter%3E%3Crect width=%22120%22 height=%22120%22 filter=%22url(%23n)%22 opacity=%220.5%22/%3E%3C/svg%3E')]" />

      <header className="relative z-10 px-4 pt-8 text-center">
        <p className="font-display text-2xl text-ink">第{round}爻</p>
        <p className="mt-1 text-sm text-ink/50">轻触屏幕或点「摇」起卦</p>
      </header>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-8 px-4 py-6">
        <AnimatePresence mode="wait">
          {phase === 'countdown' && countdownSecs > 0 && (
            <motion.div
              key="cd"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="font-display text-5xl text-gold"
            >
              {countdownSecs}
            </motion.div>
          )}
        </AnimatePresence>

        {(phase === 'toss' || phase === 'flash' || phase === 'submitting') && (
          <div className="flex gap-6">
            {[0, 1, 2].map((i) => (
              <CoinFace
                key={`${round}-${i}-${flipping}`}
                index={i}
                flipping={flipping}
                faceYang={coinFaces[i]!}
              />
            ))}
          </div>
        )}

        <AnimatePresence>
          {lastValue != null && phase === 'flash' && (
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="font-display text-xl text-gold"
            >
              {VALUE_LABEL[lastValue] ?? ''}
            </motion.p>
          )}
        </AnimatePresence>

        {error && (
          <p className="text-center text-sm text-red-700">{error}</p>
        )}

        {phase === 'submitting' && (
          <p className="font-display text-gold">排盘中…</p>
        )}
      </div>

      <div className="relative z-10 px-4 pb-10">
        <motion.button
          type="button"
          whileTap={{ scale: 0.98 }}
          disabled={phase === 'countdown' || flipping || phase === 'submitting'}
          onClick={(e) => {
            e.stopPropagation();
            doToss();
          }}
          className="w-full rounded-2xl border border-gold/40 bg-ink py-3 font-display text-lg tracking-[0.3em] text-cream disabled:opacity-40"
        >
          摇
        </motion.button>
        <p className="mt-3 text-center text-xs text-ink/40">
          已得 {coinResults.length} / 6 爻
        </p>
      </div>
    </div>
  );
}
