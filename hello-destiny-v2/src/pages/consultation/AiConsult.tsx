import { useState } from 'react';
import { motion } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';

export default function AiConsult() {
  const [text, setText] = useState('');

  return (
    <PageContainer className="flex min-h-[70vh] flex-col bg-cream pb-28 ">
      <motion.h1
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4 text-center font-display text-2xl text-ink"
      >
        AI 大师
      </motion.h1>
      <p className="mb-2 text-center font-body text-xs text-gold">20 命运点数 / 次</p>

      <div className="mx-auto flex min-h-[40vh] w-full max-w-md flex-1 flex-col rounded-2xl border border-ink/10 bg-marble/60 p-4">
        <div className="flex flex-1 items-center justify-center">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-body text-sm text-ink/45"
          >
            敬请期待
          </motion.p>
        </div>
      </div>

      <div className="mx-auto mt-4 w-full max-w-md">
        <div className="flex gap-2 rounded-2xl border border-gold/30 bg-cream p-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="输入你的问题…"
            className="min-w-0 flex-1 rounded-xl border border-transparent bg-transparent px-3 py-2 font-body text-sm text-ink outline-none placeholder:text-ink/35"
          />
          <motion.button
            type="button"
            whileTap={{ scale: 0.97 }}
            disabled
            className="rounded-xl bg-ink/20 px-4 py-2 font-body text-sm text-ink/40"
          >
            发送
          </motion.button>
        </div>
      </div>
    </PageContainer>
  );
}
