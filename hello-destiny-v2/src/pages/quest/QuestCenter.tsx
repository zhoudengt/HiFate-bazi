import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PageContainer from '../../components/layout/PageContainer';
import { useQuestStore } from '../../stores/useQuestStore';
import { questApi } from '../../api/quest';
import type { DailyQuest, MainQuest, BoxConfig } from '../../api/quest';
import { useGameStore } from '../../stores/useGameStore';

type TabKey = 'daily' | 'weekly' | 'main';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'daily', label: '日常' },
  { key: 'weekly', label: '周常' },
  { key: 'main', label: '主线' },
];

/** 与 v2_renwu_daily_config 中每日任务 tasktype 一致（仅开发环境用于联调） */
const DEV_SIMULATE_ACTIONS: { tasktype: number; label: string }[] = [
  { tasktype: 1, label: '祈福' },
  { tasktype: 2, label: '摇卦' },
  { tasktype: 3, label: '每日运势' },
  { tasktype: 4, label: '面相' },
  { tasktype: 5, label: '风水' },
];

function ActivityBar({
  current,
  boxes,
  onClaimBox,
}: {
  current: number;
  boxes: BoxConfig[];
  onClaimBox: (id: number) => void;
}) {
  const max = boxes.length > 0 ? boxes[boxes.length - 1].threshold : 100;
  const pct = Math.min(100, Math.round((current / max) * 100));

  return (
    <div className="mb-5">
      <div className="mb-1.5 flex items-center justify-between text-xs text-ink/60">
        <span>活跃值</span>
        <span>
          {current} / {max}
        </span>
      </div>
      <div className="relative h-3 w-full overflow-visible rounded-full bg-cream">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-gold to-bronze"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
        {boxes.map((b) => {
          const pos = Math.min(100, Math.round((b.threshold / max) * 100));
          const reached = current >= b.threshold;
          return (
            <button
              key={b.id}
              type="button"
              disabled={b.claimed || !reached}
              onClick={() => onClaimBox(b.id)}
              className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-md border text-[10px] font-bold transition
                ${b.claimed
                  ? 'border-jade/40 bg-jade/20 text-jade'
                  : reached
                    ? 'animate-pulse border-gold bg-gold/30 text-ink shadow-md'
                    : 'border-ink/15 bg-marble text-ink/35'
                }`}
              style={{ left: `${pos}%` }}
              title={`${b.name}：${b.reward_num} 命运点（需 ${b.threshold} 活跃）`}
            >
              {b.claimed ? '✓' : '🎁'}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DailyQuestCard({
  q,
  onClaim,
  claiming,
}: {
  q: DailyQuest;
  onClaim: (id: number) => void;
  claiming: boolean;
}) {
  const done = q.completed;
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 rounded-2xl border border-ink/10 bg-marble p-3 shadow-sm"
    >
      <img
        src="/assets/items/20001.jpg"
        alt=""
        className="h-10 w-10 shrink-0 rounded-lg object-cover"
      />
      <div className="min-w-0 flex-1">
        <h3 className="truncate font-display text-sm text-ink">{q.name}</h3>
        <div className="mt-1 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-cream">
            <div
              className="h-full rounded-full bg-gradient-to-r from-gold to-bronze transition-all duration-500"
              style={{ width: `${Math.min(100, (q.progress / q.target) * 100)}%` }}
            />
          </div>
          <span className="shrink-0 text-[10px] text-ink/50">
            {q.progress}/{q.target}
          </span>
        </div>
        <p className="mt-0.5 text-[10px] text-jade">
          +{q.reward_num} 命运点 · +{q.activity_point} 活跃
        </p>
      </div>
      <button
        type="button"
        disabled={q.claimed || !done || claiming}
        onClick={() => onClaim(q.id)}
        className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-bold transition ${
          q.claimed
            ? 'border-jade/40 bg-jade/15 text-jade'
            : done
              ? 'border-gold bg-gold/20 text-ink active:scale-95'
              : 'cursor-not-allowed border-ink/15 bg-cream text-ink/35'
        }`}
      >
        {q.claimed ? '已领' : '领取'}
      </button>
    </motion.article>
  );
}

function MainQuestCard({
  q,
  onClaim,
  claiming,
}: {
  q: MainQuest;
  onClaim: (id: number) => void;
  claiming: boolean;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 rounded-2xl border border-ink/10 bg-marble p-3 shadow-sm"
    >
      <img
        src="/assets/items/20001.jpg"
        alt=""
        className="h-10 w-10 shrink-0 rounded-lg object-cover"
      />
      <div className="min-w-0 flex-1">
        <h3 className="truncate font-display text-sm text-ink">
          {q.tasktype_label || `主线 #${q.id}`}
        </h3>
        {q.taskname && (
          <p className="mt-0.5 truncate text-[11px] text-ink/60">{q.taskname}</p>
        )}
        <p className="mt-0.5 text-[10px] text-jade">
          +{q.award_num} 命运点
        </p>
      </div>
      <button
        type="button"
        disabled={q.claimed || !q.completed || claiming}
        onClick={() => onClaim(q.id)}
        className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-bold transition ${
          q.claimed
            ? 'border-jade/40 bg-jade/15 text-jade'
            : q.completed
              ? 'border-gold bg-gold/20 text-ink active:scale-95'
              : 'cursor-not-allowed border-ink/15 bg-cream text-ink/35'
        }`}
      >
        {q.claimed ? '已领' : q.completed ? '领取' : '进行中'}
      </button>
    </motion.article>
  );
}

export default function QuestCenter() {
  const [tab, setTab] = useState<TabKey>('daily');
  const [claiming, setClaiming] = useState(false);

  const {
    daily,
    daily_boxes,
    weekly_boxes,
    daily_activity,
    weekly_activity,
    main,
    loading,
    fetchOverview,
  } = useQuestStore();

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const refresh = useCallback(async () => {
    await fetchOverview();
    useGameStore.getState().refresh();
  }, [fetchOverview]);

  const handleClaimDaily = useCallback(
    async (id: number) => {
      setClaiming(true);
      try {
        await questApi.claimDaily(id);
        await refresh();
      } finally {
        setClaiming(false);
      }
    },
    [refresh],
  );

  const handleClaimMain = useCallback(
    async (id: number) => {
      setClaiming(true);
      try {
        await questApi.claimMain(id);
        await refresh();
      } finally {
        setClaiming(false);
      }
    },
    [refresh],
  );

  const handleClaimBox = useCallback(
    async (id: number) => {
      setClaiming(true);
      try {
        await questApi.claimBox(id);
        await refresh();
      } finally {
        setClaiming(false);
      }
    },
    [refresh],
  );

  const handleSimulateAction = useCallback(
    async (tasktype: number) => {
      try {
        await questApi.recordAction(tasktype);
        await refresh();
      } catch {
        /* ignore */
      }
    },
    [refresh],
  );

  const showQuestDev = import.meta.env.DEV;

  return (
    <PageContainer className="bg-cream pb-24">
      <motion.h1
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 text-center font-display text-2xl tracking-widest text-ink"
      >
        任务中心
      </motion.h1>

      <div className="mx-auto mb-5 flex max-w-md gap-2 rounded-2xl border border-gold/30 bg-marble/60 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-xl py-2.5 font-display text-sm transition ${
              tab === t.key
                ? 'bg-ink text-cream shadow'
                : 'text-ink/70 hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {showQuestDev && (
        <div className="mx-auto mb-4 max-w-md rounded-xl border border-dashed border-amber-600/50 bg-amber-50/80 px-3 py-2 text-[11px] text-ink/80">
          <p className="mb-1.5 font-body font-medium text-amber-900/90">
            开发联调：模拟完成日常（等同调用 record-action；生产构建不显示）
          </p>
          <div className="flex flex-wrap gap-1.5">
            {DEV_SIMULATE_ACTIONS.map(({ tasktype, label }) => (
              <button
                key={tasktype}
                type="button"
                disabled={claiming}
                onClick={() => handleSimulateAction(tasktype)}
                className="rounded-md border border-amber-700/30 bg-white/90 px-2 py-1 font-body text-[10px] text-ink hover:bg-amber-100/80 disabled:opacity-50"
              >
                +{label}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && daily.length === 0 && (
        <p className="text-center text-sm text-ink/50">加载中…</p>
      )}

      <AnimatePresence mode="wait">
        {tab === 'daily' && (
          <motion.div
            key="daily"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="mx-auto max-w-md"
          >
            <ActivityBar
              current={daily_activity}
              boxes={daily_boxes}
              onClaimBox={handleClaimBox}
            />
            <div className="flex flex-col gap-3">
              {daily.map((q) => (
                <DailyQuestCard
                  key={q.id}
                  q={q}
                  onClaim={handleClaimDaily}
                  claiming={claiming}
                />
              ))}
            </div>
          </motion.div>
        )}

        {tab === 'weekly' && (
          <motion.div
            key="weekly"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="mx-auto max-w-md"
          >
            <ActivityBar
              current={weekly_activity}
              boxes={weekly_boxes}
              onClaimBox={handleClaimBox}
            />
            <p className="text-center text-sm text-ink/50">
              完成每日任务累积周活跃，解锁每周宝箱
            </p>
          </motion.div>
        )}

        {tab === 'main' && (
          <motion.div
            key="main"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="mx-auto flex max-w-md flex-col gap-3"
          >
            {main.length === 0 && !loading && (
              <p className="text-center text-sm text-ink/50">
                暂无可领取的主线任务
              </p>
            )}
            {main.map((q) => (
              <MainQuestCard
                key={q.id}
                q={q}
                onClaim={handleClaimMain}
                claiming={claiming}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </PageContainer>
  );
}
