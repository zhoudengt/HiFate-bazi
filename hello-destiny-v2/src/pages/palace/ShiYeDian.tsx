import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { SCENE_IMAGES } from '../../utils/assets';
import { PAGE_BELOW_HUD } from '../../utils/hudLayout';
import DialogueBox from '../../components/dialogue/DialogueBox';
import Modal from '../../components/common/Modal';

const INTRO_STORAGE_KEY = 'hd2.palace.shiye.intro';

export default function ShiYeDian() {
  const navigate = useNavigate();
  const [showIntro, setShowIntro] = useState(() => {
    try {
      return !localStorage.getItem(INTRO_STORAGE_KEY);
    } catch {
      return true;
    }
  });
  const [placeholderOpen, setPlaceholderOpen] = useState(false);

  const dismissIntro = () => {
    try {
      localStorage.setItem(INTRO_STORAGE_KEY, '1');
    } catch {
      /* ignore */
    }
    setShowIntro(false);
  };

  return (
    <div className="relative flex min-h-[100dvh] w-full flex-col overflow-hidden bg-ink">
      <motion.div
        className="absolute inset-0"
        initial={{ scale: 1.04, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      >
        <img
          src={SCENE_IMAGES.shiye}
          alt=""
          className="h-full w-full object-cover object-center"
        />
      </motion.div>

      <div
        className="pointer-events-none absolute inset-x-0 top-0 z-[1] h-36 bg-gradient-to-b from-black/88 via-black/45 to-transparent"
        aria-hidden
      />

      <div className={`relative z-10 flex flex-1 flex-col ${PAGE_BELOW_HUD}`}>
        <div className="pointer-events-none flex flex-1 flex-col items-center px-4 pt-4 text-center">
          <motion.h1
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4 }}
            className="font-display text-3xl text-gold drop-shadow-[0_4px_16px_rgba(0,0,0,0.85)]"
          >
            事业殿
          </motion.h1>
          <p className="mt-2 max-w-sm font-body text-sm text-cream/85">
            青云有路，问卜前程
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 mt-auto flex flex-col gap-3 px-4 pb-[max(1.25rem,env(safe-area-inset-bottom))]"
        >
          <button
            type="button"
            onClick={() => navigate('/liuyao/question?category=career')}
            className="w-full rounded-xl border-2 border-gold/80 bg-ink/75 py-3.5 font-display text-lg text-gold shadow-[0_8px_28px_rgba(0,0,0,0.5)] backdrop-blur-sm transition hover:border-gold hover:bg-ink/85 active:scale-[0.99]"
          >
            龟壳起卦
          </button>
          <button
            type="button"
            onClick={() => setPlaceholderOpen(true)}
            className="w-full rounded-xl border border-gold/45 bg-black/50 py-3 font-body text-[15px] text-cream shadow-lg backdrop-blur-sm transition hover:bg-black/60 active:scale-[0.99]"
          >
            点事业灯
          </button>
        </motion.div>
      </div>

      {showIntro ? (
        <DialogueBox
          speaker="事业殿 · 登云"
          text="功名在途，宜问天时。掷龟壳以观进退；或点事业灯，照亮前路。"
          onNext={dismissIntro}
          onSkip={dismissIntro}
        />
      ) : null}

      <Modal open={placeholderOpen} onClose={() => setPlaceholderOpen(false)} title="点事业灯">
        <p className="text-center font-body text-sm leading-relaxed text-ink/90">
          此功能即将开放，敬请期待。
        </p>
      </Modal>
    </div>
  );
}
