import type { HTMLAttributes, ReactNode } from 'react';

type CardProps = {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>;

export default function Card({ children, className = '', onClick, ...rest }: CardProps) {
  const interactive = typeof onClick === 'function';
  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`rounded-xl border border-gold/25 bg-marble/90 shadow-[0_6px_24px_rgba(26,60,52,0.12)] backdrop-blur-sm ${interactive ? 'cursor-pointer transition hover:border-gold/45 hover:shadow-[0_8px_28px_rgba(26,60,52,0.18)]' : ''} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
