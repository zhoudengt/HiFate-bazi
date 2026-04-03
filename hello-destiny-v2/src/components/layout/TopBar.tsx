import { useLayoutEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useGameStore } from '../../stores/useGameStore';
import { useUserStore } from '../../stores/useUserStore';
import { formatCompactHudNumber } from '../../utils/format';
import { UI_COPY } from '../../utils/uiCopy';
import { assetUrl } from '../../utils/assets';

function CoinIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="10" fill="currentColor" />
      <circle cx="12" cy="12" r="7.5" fill="none" stroke="rgba(0,0,0,0.25)" strokeWidth="0.8" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="0.6" fill="rgba(0,0,0,0.2)" />
    </svg>
  );
}

/** 与 App.tsx TabBar 一致：这些路径不显示顶栏返回键 */
const TAB_PATHS = ['/', '/quest', '/academy', '/v1', '/profile'];

/**
 * 全局顶栏 HUD（fixed）。
 * 仅首页 `/` 显示头像、等级、经验、命运点；非 Tab 页只显示返回键；Tab 子页以外且无返回时顶栏占位为 0。
 */
export default function TopBar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isHome = pathname === '/';
  const showBack = !TAB_PATHS.includes(pathname);
  const hideTopbarRow = !isHome && !showBack;

  const level = useGameStore((s) => s.level);
  const destinyPoints = useGameStore((s) => s.destinyPoints);
  const xp = useGameStore((s) => s.xp);
  const xpToNext = useGameStore((s) => s.xpToNext);
  const xpProgressRatio = useGameStore((s) => s.xpProgressRatio);

  const nickname = useUserStore((s) => s.nickname);
  const avatarUrl = useUserStore((s) => s.avatarUrl);
  const profileLoading = useUserStore((s) => s.profileLoading);

  const { topBar: tb } = UI_COPY;

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--topbar-h', hideTopbarRow ? '0px' : '3rem');
  }, [hideTopbarRow]);

  const pct = Math.min(100, Math.max(0, Math.round(xpProgressRatio * 100)));
  const displayName = profileLoading ? tb.nicknameLoading : nickname;
  const initial = (displayName.replace(/\s/g, '') || '?').charAt(0).toUpperCase();
  const destinyDisplay = formatCompactHudNumber(destinyPoints);
  const xpHint = tb.xpProgressTemplate(xp, xpToNext);

  const rowH = '3rem';
  const avatarW = '4.5rem';
  const levelStripW = `calc(${avatarW} * 3 / 4)`;
  const xpBarW = `calc(${avatarW} * 3 / 4 * 2)`;

  if (hideTopbarRow) {
    return null;
  }

  return (
    <header
      className="pointer-events-none fixed inset-x-0 top-0 z-50 font-body"
      style={{
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingLeft: 0,
        paddingRight: '0.75rem',
        paddingBottom: 0,
      }}
    >
      <div className="flex items-center justify-between" style={{ height: rowH }}>
        <div className="pointer-events-auto flex shrink-0 items-center gap-1.5">
          {showBack ? (
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="ml-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-amber-200/40 bg-black/40 shadow-md outline-none ring-gold/30 transition active:scale-95 focus-visible:ring-2"
              aria-label={tb.backAria}
              title={tb.backAria}
            >
              <img src={assetUrl('assets/ui/back-btn.png')} alt="" className="h-8 w-8 object-contain" draggable={false} />
            </button>
          ) : null}

          {isHome ? (
            <div className="flex shrink-0 items-stretch gap-2">
              <button
                type="button"
                onClick={() => navigate('/profile')}
                className="relative shrink-0 overflow-hidden rounded-r-lg border-2 border-l-0 border-amber-200/60 bg-black/35 shadow-[0_4px_14px_rgba(0,0,0,0.35)] outline-none ring-gold/40 transition active:scale-[0.98] focus-visible:ring-2"
                style={{ width: avatarW, height: rowH }}
                aria-label={tb.openProfileAria}
                title={tb.openProfileAria}
              >
                {avatarUrl ? (
                  <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
                ) : (
                  <span className="flex h-full w-full items-center justify-center bg-gradient-to-b from-ink/80 to-black/90 font-display text-lg text-gold/90">
                    {initial}
                  </span>
                )}
              </button>

              <div
                className="flex h-full w-max flex-col items-start justify-between"
                style={{ height: rowH }}
              >
                <div
                  className="flex shrink-0 items-center justify-center border border-amber-900/50 bg-[#ebe4d4]/95 px-1 py-0.5 shadow-sm"
                  style={{ width: levelStripW }}
                >
                  <span className="font-display text-xs font-semibold tracking-wide text-[#2c2416]">
                    {tb.levelMarkTemplate(level)}
                  </span>
                </div>
                <div className="shrink-0" style={{ width: xpBarW }}>
                  <div
                    className="rounded-sm border border-amber-900/35 bg-black/70 p-px shadow-inner"
                    title={xpHint}
                  >
                    <div className="h-1.5 overflow-hidden rounded-sm bg-black/60">
                      <div
                        className="h-full rounded-sm bg-gradient-to-r from-amber-200/90 via-amber-300 to-amber-100"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {isHome ? (
          <div
            className="pointer-events-none mr-0.5 flex min-w-[7rem] shrink-0 items-center gap-2 rounded-full border border-amber-400/45 bg-black/55 px-5 py-1.5 shadow-[0_4px_16px_rgba(0,0,0,0.4)] backdrop-blur-md"
            role="img"
            aria-label={`${tb.destinyPointsLabel} ${destinyPoints}`}
            title={`${tb.destinyPointsLabel} ${destinyPoints}`}
          >
            <CoinIcon className="h-6 w-6 shrink-0 text-amber-400 drop-shadow-sm" />
            <span className="font-body text-sm font-semibold tracking-tight text-cream tabular-nums">
              {destinyDisplay}
            </span>
          </div>
        ) : (
          <div className="min-w-0 flex-1" aria-hidden />
        )}
      </div>
    </header>
  );
}
