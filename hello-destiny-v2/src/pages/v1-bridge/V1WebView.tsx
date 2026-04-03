import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const V1_URL = 'https://www.yuanqistation.com';

export default function V1WebView() {
  const navigate = useNavigate();
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="relative flex h-full min-h-0 flex-1 flex-col bg-ink">
      <div className="flex shrink-0 items-center gap-2 border-b border-gold/20 bg-ink/95 px-3 py-2 pt-[max(0.5rem,env(safe-area-inset-top))]">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-gold/40 text-cream"
          aria-label="返回"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <span className="font-display text-sm text-gold">元气站</span>
      </div>

      <div className="relative min-h-0 flex-1">
        <AnimatePresence>
          {!loaded && (
            <motion.div
              className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-cream"
              initial={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              <motion.div
                className="h-10 w-10 rounded-full border-2 border-gold border-t-transparent"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
              />
              <p className="mt-4 font-body text-sm text-ink/70">加载中…</p>
            </motion.div>
          )}
        </AnimatePresence>
        <iframe
          title="元气站"
          src={V1_URL}
          className="h-full w-full border-0 bg-cream"
          onLoad={() => setLoaded(true)}
        />
      </div>
    </div>
  );
}
