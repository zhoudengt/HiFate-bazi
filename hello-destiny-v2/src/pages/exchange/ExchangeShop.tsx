import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { economyApi, type ShopItem } from '../../api/economy';
import { useGameStore } from '../../stores/useGameStore';
import { UI_COPY } from '../../utils/uiCopy';

const { exchange: ex } = UI_COPY;

export default function ExchangeShop() {
  const balance = useGameStore((s) => s.destinyPoints);
  const refreshGame = useGameStore((s) => s.refresh);
  const [items, setItems] = useState<ShopItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const loadShop = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await economyApi.shopItems();
      if (res.data.code === 0 && res.data.data?.items) {
        setItems(res.data.data.items);
      } else {
        setErr(ex.loadError);
      }
    } catch {
      setErr(ex.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadShop();
  }, [loadShop]);

  const onPurchase = async (listing: ShopItem) => {
    if (balance < listing.cost || busyId !== null) return;
    setBusyId(listing.listing_id);
    setToast(null);
    try {
      const res = await economyApi.purchase(listing.listing_id);
      const d = res.data;
      if (d.code === 0 && d.data?.ok) {
        setToast(ex.purchaseSuccess);
        await refreshGame();
      } else {
        setToast(d.message || ex.purchaseFail);
      }
    } catch {
      setToast(ex.purchaseFail);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <PageContainer className="bg-gradient-to-b from-marble/90 to-cream pb-24 ">
      <motion.h1
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-2 text-center font-display text-3xl tracking-[0.25em] text-ink"
      >
        {ex.title}
      </motion.h1>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="mb-2 text-center font-body text-sm text-ink/70"
      >
        {ex.balanceLabel}{' '}
        <span className="font-display text-lg text-gold">{balance}</span> {ex.pointsUnit}
      </motion.p>
      <div className="mb-6 text-center">
        <Link
          to="/inventory"
          className="font-body text-sm text-bronze underline decoration-gold/50 underline-offset-4"
        >
          {ex.viewBackpack}
        </Link>
      </div>

      {toast ? (
        <p className="mb-4 text-center font-body text-sm text-jade" role="status">
          {toast}
        </p>
      ) : null}
      {err ? (
        <p className="mb-4 text-center font-body text-sm text-red-700" role="alert">
          {err}
        </p>
      ) : null}

      {loading ? (
        <p className="text-center font-body text-ink/60">{ex.loading}</p>
      ) : (
        <motion.div
          className="mx-auto grid max-w-md grid-cols-2 gap-4"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.07 } },
          }}
        >
          {items.map((it) => (
            <motion.article
              key={it.listing_id}
              variants={{
                hidden: { opacity: 0, y: 16 },
                visible: { opacity: 1, y: 0 },
              }}
              className="flex flex-col rounded-2xl border border-gold/35 bg-cream p-4 shadow-[0_8px_24px_rgba(26,60,52,0.1)]"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border-2 border-gold/40 bg-marble">
                <img src={it.icon_url} alt="" className="h-full w-full object-cover" loading="lazy" />
              </div>
              <h2 className="mt-3 text-center font-display text-base text-ink">{it.name}</h2>
              {it.description ? (
                <p className="mt-1 line-clamp-2 text-center font-body text-[11px] text-ink/55">{it.description}</p>
              ) : null}
              <p className="mt-1 text-center font-body text-xs text-ink/50">{ex.grantNoteTemplate(it.quantity)}</p>
              <p className="mt-1 text-center font-body text-sm text-gold">{ex.costTemplate(it.cost)}</p>
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                disabled={balance < it.cost || busyId !== null}
                onClick={() => void onPurchase(it)}
                className="mt-4 w-full rounded-xl border border-ink/15 bg-ink py-2 font-display text-sm text-cream disabled:opacity-40"
              >
                {balance < it.cost ? ex.redeemDisabled : busyId === it.listing_id ? '…' : ex.redeemButton}
              </motion.button>
            </motion.article>
          ))}
        </motion.div>
      )}
    </PageContainer>
  );
}
