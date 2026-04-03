import { useMemo } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useLiuyaoStore } from '../../stores/useLiuyaoStore';

type LineRow = {
  position?: number;
  yin_yang?: string;
  is_dong?: boolean;
  liu_qin?: string;
  liu_shen?: string;
  yao_ci?: string;
};

type GuaBlock = {
  name?: string;
  lines?: LineRow[];
};

type HexagramPayload = {
  ben_gua?: GuaBlock;
  bian_gua?: GuaBlock;
  gua_ci?: string;
  shi_ying?: { shi_yao?: number; ying_yao?: number };
  gong?: string;
  gong_wuxing?: string;
};

function LineBar({
  line,
  shi,
  ying,
}: {
  line: LineRow;
  shi?: number;
  ying?: number;
}) {
  const yin = line.yin_yang !== 'yang';
  const dong = !!line.is_dong;
  const pos = line.position ?? 0;
  const marker = pos === shi ? '世' : pos === ying ? '应' : null;
  return (
    <div
      className={`flex items-center gap-2 ${dong ? 'rounded-md ring-2 ring-gold/70' : ''}`}
    >
      <span className="flex w-9 shrink-0 justify-end gap-0.5 text-xs text-ink/50">
        {marker && <span className="text-gold">{marker}</span>}
        <span>{pos}</span>
      </span>
      <div className="flex flex-1 flex-col gap-1">
        {yin ? (
          <div className="flex w-full justify-center gap-[12%]">
            <div className="h-2 flex-1 rounded-sm bg-ink/85" />
            <div className="h-2 flex-1 rounded-sm bg-ink/85" />
          </div>
        ) : (
          <div className="h-2 w-full rounded-sm bg-ink/85" />
        )}
      </div>
      <div className="w-24 shrink-0 text-right text-xs text-ink/70">
        <span className="text-gold">{line.liu_qin ?? '—'}</span>
        <span className="text-ink/40"> · </span>
        <span>{line.liu_shen ?? '—'}</span>
      </div>
      {dong && (
        <span className="shrink-0 rounded bg-gold/25 px-1.5 py-0.5 text-[10px] text-gold">动</span>
      )}
    </div>
  );
}

function GuaColumn({ title, block, shi, ying }: { title: string; block?: GuaBlock; shi?: number; ying?: number }) {
  const lines = block?.lines ?? [];
  const ordered = [...lines].sort((a, b) => (b.position ?? 0) - (a.position ?? 0));
  return (
    <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-ink/10 bg-cream/90 p-3 shadow-sm">
      <h3 className="mb-3 text-center font-display text-lg text-ink">{title}</h3>
      <p className="mb-3 text-center font-display text-xl text-gold">{block?.name ?? '—'}</p>
      <div className="flex flex-col gap-2">
        {ordered.map((line) => (
          <LineBar
            key={`${title}-${line.position}`}
            line={line}
            shi={shi}
            ying={ying}
          />
        ))}
      </div>
      <div className="mt-3 border-t border-ink/10 pt-2 text-center text-[11px] text-ink/45">
        自下而上为初爻至上爻；此列自上而下对应上爻至初爻
      </div>
    </div>
  );
}

export default function HexagramResult() {
  const navigate = useNavigate();
  const { id: routeId } = useParams();
  const hexagramData = useLiuyaoStore((s) => s.hexagramData) as HexagramPayload | null;
  const castingId = useLiuyaoStore((s) => s.castingId);

  const data = hexagramData;
  const shi = data?.shi_ying?.shi_yao;
  const ying = data?.shi_ying?.ying_yao;

  const reading = useMemo(() => {
    const parts: string[] = [];
    if (data?.gua_ci) parts.push(data.gua_ci);
    const benLines = data?.ben_gua?.lines ?? [];
    benLines.forEach((ln) => {
      if (ln.yao_ci) parts.push(`第${ln.position ?? ''}爻：${ln.yao_ci}`);
    });
    return parts.join('\n\n');
  }, [data]);

  if (!data?.ben_gua) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-4 bg-marble px-6 font-body text-ink">
        <p className="text-center text-ink/60">暂无卦象，请先起卦</p>
        <Link
          to="/liuyao/question"
          className="rounded-full bg-gold px-6 py-2 font-display text-ink"
        >
          去提问
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-marble font-body text-ink">
      <div className="mx-auto max-w-lg px-4 py-6">
        <motion.header
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 text-center"
        >
          <h1 className="font-display text-3xl tracking-widest text-ink">
            {data.ben_gua?.name ?? '卦'}
          </h1>
          <p className="mt-2 text-sm text-ink/50">
            {castingId != null
              ? `编号 · ${castingId}`
              : routeId && routeId !== '0'
                ? `记录 · ${routeId}`
                : '本次占得'}
          </p>
        </motion.header>

        <div className="mb-4 flex flex-wrap justify-center gap-3 rounded-xl border border-gold/25 bg-cream/80 px-3 py-2 text-sm">
          <span>
            宫：<strong className="text-gold">{data.gong ?? '—'}</strong>
            {data.gong_wuxing ? `（${data.gong_wuxing}）` : ''}
          </span>
          <span className="text-ink/30">|</span>
          <span>
            世爻 <strong className="text-gold">{shi ?? '—'}</strong>
          </span>
          <span>
            应爻 <strong className="text-gold">{ying ?? '—'}</strong>
          </span>
        </div>

        <div className="flex flex-col gap-4 md:flex-row">
          <GuaColumn title="本卦" block={data.ben_gua} shi={shi} ying={ying} />
          <GuaColumn title="变卦" block={data.bian_gua} shi={shi} ying={ying} />
        </div>

        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="mt-6 rounded-xl border border-ink/10 bg-cream px-4 py-4 text-left"
        >
          <h2 className="mb-2 font-display text-lg text-gold">卦辞与爻辞</h2>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink/85">
            {reading || '（无文本）'}
          </p>
        </motion.section>

        <div className="mt-8 pb-8">
          <motion.button
            type="button"
            whileTap={{ scale: 0.99 }}
            onClick={() => navigate('/liuyao/ai/0')}
            className="w-full rounded-2xl bg-gold py-4 font-display text-lg tracking-[0.15em] text-ink shadow-md shadow-gold/20"
          >
            AI 深度解读
          </motion.button>
        </div>
      </div>
    </div>
  );
}
