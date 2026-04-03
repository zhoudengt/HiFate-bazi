import { motion, AnimatePresence } from 'framer-motion';

export type DialogueSide = 'left' | 'right';

import { assetUrl } from '../../utils/assets';

const DIALOGUE_FRAME = assetUrl('assets/dialogue/frame.png');
const DIALOGUE_NAMEPLATE = assetUrl('assets/dialogue/nameplate.png');
const DIALOGUE_ARROW = assetUrl('assets/dialogue/arrow.png');

type DialogueBoxProps = {
  speaker: string;
  avatar?: string;
  text: string;
  onNext: () => void;
  /** 点击「跳过」结束整段剧情；不传则不显示跳过 */
  onSkip?: () => void;
  /** 立绘在左（卦师等）或右（玩家自己）；默认 left */
  side?: DialogueSide;
};

/**
 * 视觉小说式剧情：立绘 + 羊皮纸底框（PNG）+ 名牌 + 箭头；全屏点按进入下一句。
 */
export default function DialogueBox({
  speaker,
  avatar,
  text,
  onNext,
  onSkip,
  side = 'left',
}: DialogueBoxProps) {
  const isRight = side === 'right';

  return (
    <div className="fixed inset-0 z-50 flex flex-col font-body">
      {/* 压暗场景 */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/25 via-black/35 to-black/55" aria-hidden />

      {onSkip ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSkip();
          }}
          className="pointer-events-auto absolute right-4 z-[60] px-2 py-1 font-body text-sm font-medium tracking-wide text-white/95 drop-shadow-[0_1px_4px_rgba(0,0,0,0.85)] outline-none transition hover:text-white focus-visible:ring-2 focus-visible:ring-gold/70"
          style={{ top: 'max(0.5rem, env(safe-area-inset-top))' }}
          aria-label="跳过剧情"
        >
          跳过
        </button>
      ) : null}

      <div
        role="button"
        tabIndex={0}
        onClick={onNext}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onNext();
          }
        }}
        className="relative z-10 flex min-h-0 flex-1 cursor-pointer flex-col outline-none focus-visible:ring-2 focus-visible:ring-gold/60 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
        aria-label={`${speaker}：${text}。点击继续`}
      >
        {/* 上方留白可点下一页 */}
        <div className="min-h-0 flex-1" aria-hidden />

        {/* 底栏：frame 为定位锚点，立绘站在 frame 上沿，名牌 3/4 压在 frame 上 */}
        <div
          className="w-full shrink-0 px-3"
          style={{
            marginBottom: 'max(12vh, env(safe-area-inset-bottom))',
            paddingBottom: '0.25rem',
          }}
        >
          <div className="relative mx-auto w-[min(94vw,26rem)]">
            {/* 立绘：底边贴 frame 上沿 */}
            <AnimatePresence mode="wait">
              <motion.div
                key={`${speaker}-${text.slice(0, 24)}`}
                initial={{ opacity: 0, x: isRight ? 40 : -40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ type: 'spring', stiffness: 320, damping: 28 }}
                className={`pointer-events-none absolute inset-x-0 z-10 flex items-end ${
                  isRight ? 'justify-end pr-1' : 'justify-start pl-1'
                }`}
                style={{ bottom: '97%', height: 'min(52dvh, 55vh)' }}
              >
                {avatar ? (
                  <img
                    src={avatar}
                    alt=""
                    className="max-h-full w-auto max-w-[min(92vw,22rem)] object-contain object-bottom drop-shadow-[0_8px_32px_rgba(0,0,0,0.65)] sm:max-w-[min(88vw,24rem)]"
                    draggable={false}
                  />
                ) : (
                  <div className="flex h-44 w-40 max-h-full items-center justify-center rounded-xl border-2 border-gold/50 bg-black/50 font-display text-5xl text-gold shadow-2xl backdrop-blur-sm sm:h-52 sm:w-44">
                    言
                  </div>
                )}
              </motion.div>
            </AnimatePresence>

            {/* 名牌：absolute，3/4 压在 frame 上沿内 */}
            <div
              className={`absolute z-20 flex ${isRight ? 'right-1' : 'left-1'}`}
              style={{ top: '-1.5rem' }}
            >
              <div
                className={`relative flex h-11 min-w-[7.5rem] max-w-[70%] items-stretch justify-center sm:h-12 ${isRight ? 'scale-x-[-1]' : ''}`}
              >
                <img
                  src={DIALOGUE_NAMEPLATE}
                  alt=""
                  className="h-full w-auto max-w-full object-contain object-left"
                  draggable={false}
                />
                <span
                  className={`absolute inset-0 flex items-center justify-center px-5 pt-0.5 font-display text-xs font-semibold tracking-wide text-amber-100 drop-shadow-sm sm:text-sm ${isRight ? 'scale-x-[-1]' : ''}`}
                >
                  {speaker}
                </span>
              </div>
            </div>

            {/* 底框 PNG */}
            <img
              src={DIALOGUE_FRAME}
              alt=""
              className="relative z-0 block w-full select-none"
              draggable={false}
            />

            {/* 文本：左对齐、靠上 */}
            <div className="absolute inset-[25%_7%_14%_7%] z-10 flex flex-col justify-start sm:inset-[25%_8%_14%_8%]">
              <p className="text-left text-[15px] leading-relaxed text-[#2a1e14] sm:text-base">{text}</p>
            </div>

            {/* 箭头 */}
            <div className="pointer-events-none absolute bottom-[7%] right-[7%] z-10 sm:bottom-[8%] sm:right-[8%]">
              <img
                src={DIALOGUE_ARROW}
                alt=""
                className="h-4 w-auto animate-pulse opacity-95 sm:h-5"
                draggable={false}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
