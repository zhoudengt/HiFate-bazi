import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { economyApi, type InventoryItem } from '../../api/economy';
import { UI_COPY } from '../../utils/uiCopy';
import { assetUrl } from '../../utils/assets';

const { inventory: inv } = UI_COPY;

export default function InventoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await economyApi.inventory();
      if (res.data.code === 0 && res.data.data?.items) {
        setItems(res.data.data.items);
      }
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <PageContainer className="bg-gradient-to-b from-cream to-marble/80 pb-28 ">
      <header className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/20 bg-marble text-ink shadow-sm"
          aria-label="返回"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <h1 className="font-display text-xl text-ink">{inv.title}</h1>
      </header>

      {loading ? (
        <p className="text-center font-body text-ink/60">…</p>
      ) : items.length === 0 ? (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mx-auto max-w-md text-center font-body text-sm text-ink/65"
        >
          {inv.empty}
        </motion.p>
      ) : (
        <motion.div
          className="mx-auto grid max-w-md grid-cols-2 gap-4"
          initial="hidden"
          animate="visible"
          variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}
        >
          {items.map((it) => (
            <motion.article
              key={it.item_id}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0 },
              }}
              className="flex flex-col rounded-2xl border border-gold/30 bg-marble/90 p-3 shadow-sm"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center overflow-hidden rounded-xl border border-gold/35 bg-cream">
                <img src={assetUrl(it.icon_url)} alt="" className="h-full w-full object-cover" loading="lazy" />
              </div>
              <h2 className="mt-2 text-center font-display text-sm text-ink">{it.name}</h2>
              <p className="mt-1 text-center font-body text-xs text-gold">{inv.quantityLabel(it.quantity)}</p>
            </motion.article>
          ))}
        </motion.div>
      )}

      <div className="mx-auto mt-10 max-w-md text-center">
        <Link
          to="/exchange"
          className="inline-block rounded-xl border border-ink/20 bg-ink px-6 py-2.5 font-display text-sm text-cream"
        >
          {inv.backToShop}
        </Link>
      </div>
    </PageContainer>
  );
}
