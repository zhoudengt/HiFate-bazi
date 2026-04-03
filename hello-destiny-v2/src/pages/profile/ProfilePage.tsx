import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { useGameStore } from '../../stores/useGameStore';
import { useUserStore } from '../../stores/useUserStore';
import { UI_COPY } from '../../utils/uiCopy';

export default function ProfilePage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const level = useGameStore((s) => s.level);
  const points = useGameStore((s) => s.destinyPoints);
  const xp = useGameStore((s) => s.xp);
  const xpToNext = useGameStore((s) => s.xpToNext);
  const xpProgressRatio = useGameStore((s) => s.xpProgressRatio);
  const userId = useUserStore((s) => s.userId);
  const nickname = useUserStore((s) => s.nickname);
  const avatarUrl = useUserStore((s) => s.avatarUrl);
  const uploadAvatar = useUserStore((s) => s.uploadAvatar);
  const updateNickname = useUserStore((s) => s.updateNickname);
  const profileLoading = useUserStore((s) => s.profileLoading);

  const [nickDraft, setNickDraft] = useState('');
  const [nickSaving, setNickSaving] = useState(false);
  const { profile: pc } = UI_COPY;

  const pct = Math.round(Math.min(1, Math.max(0, xpProgressRatio)) * 100);

  const MENU = [
    { label: pc.menuBadge, path: '/badge' },
    { label: UI_COPY.inventory.menuLabel, path: '/inventory' },
    { label: pc.menuLiuyaoHistory, path: '/liuyao/question' },
    { label: pc.menuSettings, path: '/v1' },
    { label: pc.menuAbout, path: '/invite' },
  ];

  const onPickAvatar = () => fileRef.current?.click();

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    await uploadAvatar(f);
  };

  const onSaveNickname = async () => {
    setNickSaving(true);
    const next = (nickDraft || nickname).trim();
    const ok = await updateNickname(next);
    if (ok) setNickDraft('');
    setNickSaving(false);
  };

  return (
    <PageContainer className="bg-cream pb-28 ">
      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/gif,image/webp" className="hidden" onChange={onFileChange} />

      <motion.div
        className="mx-auto flex max-w-md flex-col items-center"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <button
          type="button"
          onClick={onPickAvatar}
          className="relative flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border-4 border-gold bg-marble shadow-lg transition active:scale-[0.98]"
          aria-label={pc.uploadAvatar}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
          ) : (
            <svg className="h-16 w-16 text-gold/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <circle cx="12" cy="9" r="4" />
              <path d="M5 21v-1a7 7 0 0 1 14 0v1" />
            </svg>
          )}
          <span className="absolute bottom-1 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-2 py-0.5 font-body text-[10px] text-cream">
            {pc.changeAvatarHint}
          </span>
        </button>

        <p className="mt-4 font-display text-xl text-ink">{nickname}</p>
        <p className="mt-1 font-body text-xs text-ink/55">
          {pc.idLabel}：{userId ?? pc.statPlaceholder}
        </p>
        <span className="mt-2 inline-flex rounded-full border border-gold/50 bg-ink px-4 py-1 font-body text-xs text-gold">
          {pc.levelBadgeTemplate(level)}
        </span>
      </motion.div>

      <motion.div
        className="mx-auto mt-8 w-full max-w-md rounded-2xl border border-ink/10 bg-marble/90 p-4 shadow-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.05 }}
      >
        <p className="font-body text-xs text-ink/60">{pc.nicknamePlaceholder}</p>
        <div className="mt-2 flex gap-2">
          <input
            value={nickDraft !== '' ? nickDraft : nickname}
            onChange={(e) => setNickDraft(e.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-ink/15 bg-cream px-3 py-2 font-body text-sm text-ink"
            maxLength={50}
          />
          <button
            type="button"
            disabled={nickSaving || profileLoading}
            onClick={onSaveNickname}
            className="shrink-0 rounded-xl border border-gold bg-ink px-4 py-2 font-display text-sm text-cream disabled:opacity-50"
          >
            {pc.saveNickname}
          </button>
        </div>
      </motion.div>

      <motion.div
        className="mx-auto mt-6 w-full max-w-md rounded-2xl border border-gold/30 bg-ink/5 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.08 }}
      >
        <p className="font-body text-xs text-ink/60">{UI_COPY.topBar.xpShortLabel}</p>
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className="font-mono text-ink">{UI_COPY.topBar.xpProgressTemplate(xp, xpToNext)}</span>
          <span className="text-gold">{pct}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink/10">
          <div className="h-full rounded-full bg-gradient-to-r from-gold to-bronze" style={{ width: `${pct}%` }} />
        </div>
      </motion.div>

      <motion.div
        className="mx-auto mt-8 grid max-w-md grid-cols-3 gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {[
          { label: pc.destinyPointsStat, value: points },
          { label: pc.castCountStat, value: pc.statPlaceholder },
          { label: pc.studyDaysStat, value: pc.statPlaceholder },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-2xl border border-ink/10 bg-marble px-2 py-4 text-center shadow-sm"
          >
            <p className="font-display text-lg text-gold">{s.value}</p>
            <p className="mt-1 font-body text-[11px] text-ink/60">{s.label}</p>
          </div>
        ))}
      </motion.div>

      <motion.section
        className="mx-auto mt-8 max-w-md rounded-2xl border border-bronze/25 bg-gradient-to-b from-marble/90 to-cream/80 p-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
      >
        <h2 className="font-display text-base text-ink">{pc.progressTitle}</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 font-body text-sm leading-relaxed text-ink/75">
          {pc.progressHints.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </motion.section>

      <motion.nav
        className="mx-auto mt-10 max-w-md overflow-hidden rounded-2xl border border-gold/25 bg-marble/80"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        {MENU.map((m, i) => (
          <button
            key={m.path}
            type="button"
            onClick={() => navigate(m.path)}
            className={`flex w-full items-center justify-between px-5 py-4 text-left font-display text-ink transition hover:bg-gold/10 ${
              i < MENU.length - 1 ? 'border-b border-ink/10' : ''
            }`}
          >
            {m.label}
            <svg className="h-4 w-4 text-gold/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        ))}
      </motion.nav>
    </PageContainer>
  );
}
