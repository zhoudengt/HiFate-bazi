import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { PAGE_BELOW_HUD } from '../../utils/hudLayout';
import { getSceneBg } from '../../utils/assets';

export type AcademyLayoutProps = {
  children: ReactNode;
  /** 201/202 等；不传则仅显示暗色氛围底（章节总览） */
  bgCode?: string | number | null;
  title?: string;
  subtitle?: string;
  /** 标题居中（如学堂首页） */
  titleCenter?: boolean;
  loading?: boolean;
  loadingText?: string;
  error?: string | null;
  showBack?: boolean;
  onBack?: () => void;
  /** 滚动区内额外 class */
  scrollClassName?: string;
};

/**
 * 学堂全屏页统一布局：背景图用 absolute 铺在根容器内，避免在 overflow 父级里用 fixed + 负 z-index 导致不显示。
 */
export default function AcademyLayout({
  children,
  bgCode,
  title,
  subtitle,
  titleCenter = false,
  loading = false,
  loadingText = '载入…',
  error = null,
  showBack = true,
  onBack,
  scrollClassName = '',
}: AcademyLayoutProps) {
  const hasScene = bgCode != null && String(bgCode).length > 0;
  const bgUrl = hasScene ? getSceneBg(bgCode) : null;

  return (
    <div className="relative flex min-h-0 min-h-[100dvh] w-full flex-1 flex-col overflow-hidden">
      {hasScene && bgUrl ? (
        <>
          <img
            src={bgUrl}
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-cover object-center"
            loading="lazy"
          />
          <div
            className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/50 via-black/70 to-[#0f1210]/95"
            aria-hidden
          />
        </>
      ) : (
        <div
          className="pointer-events-none absolute inset-0 bg-[#0a0e14]"
          style={{
            backgroundImage:
              'radial-gradient(ellipse 70% 45% at 50% 20%, rgba(100,80,140,0.45) 0%, transparent 55%), radial-gradient(ellipse 50% 35% at 80% 85%, rgba(40,70,90,0.4) 0%, transparent 50%)',
          }}
          aria-hidden
        />
      )}

      <div
        className={`relative z-10 flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-28 ${PAGE_BELOW_HUD} ${scrollClassName}`}
      >
        {(showBack || title) && !titleCenter ? (
          <header className="mb-4 flex shrink-0 items-center gap-3 pt-1">
            {showBack && onBack ? (
              <motion.button
                type="button"
                whileTap={{ scale: 0.96 }}
                onClick={onBack}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#c9a227]/55 bg-black/40 text-[#d4af6a] backdrop-blur-sm"
                aria-label="返回"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </motion.button>
            ) : null}
            {title ? (
              <div className="min-w-0 flex-1">
                {subtitle ? (
                  <div className="rounded-r-xl border border-[#c9a227]/35 bg-[#1a1815]/75 px-3 py-2 pr-4 backdrop-blur-md">
                    <h1 className="font-display text-lg text-[#f5ecd8] drop-shadow sm:text-xl">{title}</h1>
                    <p className="mt-0.5 font-body text-xs text-[#d4c4a8]/90">{subtitle}</p>
                  </div>
                ) : (
                  <h1 className="font-display text-lg text-[#f5ecd8] drop-shadow-md sm:text-xl">{title}</h1>
                )}
              </div>
            ) : null}
          </header>
        ) : null}

        {titleCenter && title ? (
          <motion.h1
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 shrink-0 text-center font-display text-3xl tracking-[0.25em] text-[#d4af6a] drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]"
          >
            {title}
          </motion.h1>
        ) : null}

        {loading ? (
          <p className="shrink-0 text-center font-body text-[#e8dcc8]/75">{loadingText}</p>
        ) : error ? (
          <p className="shrink-0 text-center font-body text-sm text-red-300" role="alert">
            {error}
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
