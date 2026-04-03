import { useMemo, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LIUYAO_CATEGORIES } from '../../utils/constants';
import { useLiuyaoStore } from '../../stores/useLiuyaoStore';

const EXTRA_LIUYAO_TAGS = [
  { key: 'pregnancy', label: '胎孕' },
  { key: 'official', label: '官宦' },
  { key: 'illness', label: '疾病' },
  { key: 'property', label: '田宅' },
  { key: 'lost', label: '失物' },
  { key: 'travel', label: '出行' },
] as const;

const ALL_TAGS = [...LIUYAO_CATEGORIES, ...EXTRA_LIUYAO_TAGS];

type LiuyaoKey = (typeof ALL_TAGS)[number]['key'];

const VALID_KEYS = new Set<string>(ALL_TAGS.map((t) => t.key));

export default function QuestionInput() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setQuestion = useLiuyaoStore((s) => s.setQuestion);
  const setCategory = useLiuyaoStore((s) => s.setCategory);
  const storeQuestion = useLiuyaoStore((s) => s.question);
  const storeCategory = useLiuyaoStore((s) => s.category);

  const [text, setText] = useState(storeQuestion);
  const [category, setLocalCategory] = useState<LiuyaoKey>(() =>
    VALID_KEYS.has(storeCategory) ? (storeCategory as LiuyaoKey) : 'general',
  );

  const urlCategory = searchParams.get('category');
  useEffect(() => {
    if (urlCategory && VALID_KEYS.has(urlCategory)) {
      const k = urlCategory as LiuyaoKey;
      setLocalCategory(k);
      setCategory(k);
    }
  }, [urlCategory, setCategory]);

  const maxLen = 200;
  const canSubmit = text.trim().length > 0;

  const tags = useMemo(() => ALL_TAGS, []);

  const submit = () => {
    if (!canSubmit) return;
    setQuestion(text.trim().slice(0, maxLen));
    setCategory(category);
    navigate('/liuyao/casting');
  };

  return (
    <div className="flex min-h-full flex-col bg-marble font-body text-ink">
      <div className="border-b border-gold/20 bg-cream/80 px-3 py-3 backdrop-blur-sm">
        <p className="mb-2 text-center font-display text-sm tracking-widest text-gold">问卦类别</p>
        <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {tags.map((tag) => {
            const active = category === tag.key;
            return (
              <motion.button
                key={tag.key}
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => setLocalCategory(tag.key)}
                className={`shrink-0 rounded-full px-3.5 py-1.5 text-sm transition-colors ${
                  active
                    ? 'bg-gold text-ink shadow-sm'
                    : 'bg-marble text-ink/80 ring-1 ring-ink/10'
                }`}
              >
                {tag.label}
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-1 flex-col px-4 py-6">
        <label className="mb-2 block text-left text-sm text-ink/70">所问何事</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, maxLen))}
          placeholder="今天运适合做什么？"
          rows={6}
          className="w-full flex-1 min-h-[160px] resize-none rounded-xl border border-ink/15 bg-cream px-4 py-3 font-body text-ink placeholder:text-ink/35 focus:border-gold/60 focus:outline-none focus:ring-1 focus:ring-gold/40"
        />
        <div className="mt-2 flex justify-end text-xs text-ink/45">
          {text.length}/{maxLen}
        </div>
      </div>

      <div className="sticky bottom-0 bg-gradient-to-t from-marble via-marble to-transparent px-4 pb-8 pt-4">
        <motion.button
          type="button"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          disabled={!canSubmit}
          onClick={submit}
          className="w-full rounded-2xl bg-gold py-4 font-display text-lg tracking-[0.2em] text-ink shadow-lg shadow-gold/25 disabled:opacity-40"
        >
          静气凝神
        </motion.button>
      </div>
    </div>
  );
}
