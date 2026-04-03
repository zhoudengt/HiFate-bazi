import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { liuyaoApi, type DivinateRequest } from '../../api/liuyao';
import { useLiuyaoStore } from '../../stores/useLiuyaoStore';

type SsePayload = {
  type?: string;
  content?: unknown;
};

function parseSseBlock(block: string): SsePayload | null {
  const line = block.trim();
  if (!line.startsWith('data:')) return null;
  const json = line.slice(5).trim();
  if (!json) return null;
  try {
    return JSON.parse(json) as SsePayload;
  } catch {
    return null;
  }
}

export default function AiAnalysis() {
  const navigate = useNavigate();
  const question = useLiuyaoStore((s) => s.question);
  const category = useLiuyaoStore((s) => s.category);
  const method = useLiuyaoStore((s) => s.method);
  const coinResults = useLiuyaoStore((s) => s.coinResults);
  const appendAiText = useLiuyaoStore((s) => s.appendAiText);
  const resetAiText = useLiuyaoStore((s) => s.resetAiText);
  const resetAll = useLiuyaoStore((s) => s.resetAll);
  const aiText = useLiuyaoStore((s) => s.aiText);

  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    resetAiText();
    setError(null);
    setDone(false);

    const payload: DivinateRequest = {
      question,
      method,
      category,
      coin_results: coinResults.length === 6 ? coinResults : undefined,
    };

    if (!question.trim() || !payload.coin_results) {
      setError('缺少起卦数据，请返回重试');
      setDone(true);
      return;
    }

    const ac = new AbortController();
    abortRef.current = ac;

    const run = async () => {
      try {
        const token = localStorage.getItem('v2_token');
        const res = await fetch(liuyaoApi.streamUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ ...payload, persist: false }),
          signal: ac.signal,
        });

        if (!res.ok || !res.body) {
          setError(`请求失败 (${res.status})`);
          setDone(true);
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { value, done: streamDone } = await reader.read();
          if (streamDone) break;
          buffer += decoder.decode(value, { stream: true });
          buffer = buffer.replace(/\r\n/g, '\n');
          const parts = buffer.split('\n\n');
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            const msg = parseSseBlock(part);
            if (!msg?.type) continue;
            if (msg.type === 'progress' && typeof msg.content === 'string') {
              appendAiText(msg.content);
            } else if (msg.type === 'complete') {
              setDone(true);
            } else if (msg.type === 'error') {
              setError(String(msg.content ?? '解读中断'));
              setDone(true);
            }
          }
        }

        const tail = buffer.trim();
        if (tail) {
          const msg = parseSseBlock(tail.includes('\n') ? tail.split('\n').pop() ?? '' : tail);
          if (msg?.type === 'progress' && typeof msg.content === 'string') {
            appendAiText(msg.content);
          }
        }
        setDone(true);
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
        setError(e instanceof Error ? e.message : '流式读取失败');
        setDone(true);
      }
    };

    void run();
    return () => {
      ac.abort();
    };
  }, [appendAiText, category, coinResults, method, question, resetAiText]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [aiText]);

  return (
    <div className="flex min-h-full flex-col bg-cream font-body text-ink">
      <div className="border-b border-gold/20 bg-marble/90 px-4 py-3 text-center text-sm text-ink/80">
        开通会员可每日免费AI解读
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}

        <motion.article
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="max-w-none text-left"
        >
          <AnimatePresence mode="popLayout">
            <motion.div
              key={aiText.length}
              initial={{ opacity: 0.35 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.35 }}
              className="whitespace-pre-wrap font-body text-base leading-[1.75] tracking-wide text-ink"
            >
              {aiText}
              {!done && !error && (
                <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-gold align-middle" />
              )}
            </motion.div>
          </AnimatePresence>
        </motion.article>
      </div>

      <AnimatePresence>
        {done && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="border-t border-ink/10 bg-marble/95 px-4 pb-10 pt-4"
          >
            <div className="mx-auto flex max-w-md flex-col gap-3">
              <button
                type="button"
                onClick={() => {
                  resetAll();
                  navigate('/liuyao/question');
                }}
                className="w-full rounded-2xl bg-gold py-3 font-display tracking-wider text-ink"
              >
                再问一卦
              </button>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="w-full rounded-2xl border border-ink/15 bg-cream py-3 font-display tracking-wider text-ink"
              >
                返回首页
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
