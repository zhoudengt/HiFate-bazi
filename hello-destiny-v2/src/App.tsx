import { Suspense, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import TabBar from './components/layout/TabBar';
import TopBar from './components/layout/TopBar';
import Loading from './components/common/Loading';
import { useUserStore } from './stores/useUserStore';
import { ensureGuestToken } from './utils/guestToken';

const TAB_PATHS = ['/', '/quest', '/academy', '/v1', '/profile'];

export default function AppLayout() {
  const location = useLocation();
  const showTabBar = TAB_PATHS.includes(location.pathname);
  const fetchProfile = useUserStore((s) => s.fetchProfile);

  useEffect(() => {
    ensureGuestToken();
    void fetchProfile();
  }, [fetchProfile]);

  return (
    <div className="relative flex flex-col w-full h-full bg-cream">
      <TopBar />

      <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full"
          >
            <Suspense fallback={<Loading />}>
              <Outlet />
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </main>

      {showTabBar && <TabBar />}
    </div>
  );
}
