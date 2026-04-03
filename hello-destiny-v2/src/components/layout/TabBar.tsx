import { useLocation, useNavigate } from 'react-router-dom';
import { UI_COPY } from '../../utils/uiCopy';

function PalaceIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M4 10L12 4l8 6v10H4V10z" strokeLinejoin="round" />
      <path d="M9 20v-6h6v6" strokeLinejoin="round" />
    </svg>
  );
}

function ScrollIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M8 4h8a2 2 0 012 2v14l-4-2-4 2-4-2-4 2V6a2 2 0 012-2z" strokeLinejoin="round" />
      <path d="M8 9h8M8 13h5" strokeLinecap="round" />
    </svg>
  );
}

function BookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M5 4h7a2 2 0 012 2v14a2 2 0 00-2-2H5V4z" strokeLinejoin="round" />
      <path d="M19 4h-7a2 2 0 00-2 2v14a2 2 0 002-2h7V4z" strokeLinejoin="round" />
    </svg>
  );
}

function CompassIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v10M7 12h10" strokeLinecap="round" />
      <path d="M14.5 9.5L12 12l-2.5 2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20v-1a5 5 0 015-5h4a5 5 0 015 5v1" strokeLinejoin="round" />
    </svg>
  );
}

const TAB_ICONS = [PalaceIcon, ScrollIcon, BookIcon, CompassIcon, UserIcon] as const;

const tabs = UI_COPY.nav.tabs.map((t, i) => ({
  label: t.label,
  path: t.path,
  Icon: TAB_ICONS[i],
}));

function isTabActive(pathname: string, tabPath: string): boolean {
  if (tabPath === '/') return pathname === '/' || pathname === '';
  if (tabPath === '/academy') return pathname.startsWith('/academy');
  if (tabPath === '/liuyao/question') return pathname.startsWith('/liuyao');
  if (tabPath === '/quest') return pathname.startsWith('/quest');
  if (tabPath === '/profile') return pathname.startsWith('/profile');
  return pathname.startsWith(tabPath);
}

export default function TabBar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-white/10 bg-[#1a1a1a] pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1 font-body text-[11px] text-zinc-500 shadow-[0_-4px_20px_rgba(0,0,0,0.35)]"
      aria-label={UI_COPY.nav.mainNavAria}
    >
      <div className="mx-auto flex max-w-lg items-end justify-between px-2">
        {tabs.map(({ label, path, Icon }) => {
          const active = isTabActive(pathname, path);
          return (
            <button
              key={path}
              type="button"
              onClick={() => navigate(path)}
              className="flex min-w-0 flex-1 flex-col items-center gap-0.5 py-1.5 transition-colors"
            >
              <Icon className={`h-6 w-6 shrink-0 ${active ? 'text-gold' : 'text-zinc-500'}`} />
              <span className={`truncate ${active ? 'font-medium text-gold' : 'text-zinc-500'}`}>{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
