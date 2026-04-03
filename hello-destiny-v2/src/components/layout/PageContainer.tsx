import type { ReactNode } from 'react';
import { PAGE_BELOW_HUD } from '../../utils/hudLayout';

type PageContainerProps = {
  children: ReactNode;
  className?: string;
};

/**
 * 通用页面容器。
 * padding-top 与元辰宫/各殿全屏页同源（PAGE_BELOW_HUD / --page-top）。
 */
export default function PageContainer({ children, className = '' }: PageContainerProps) {
  return (
    <div className={`box-border min-h-0 flex-1 overflow-y-auto px-4 pb-4 ${PAGE_BELOW_HUD} ${className}`}>
      {children}
    </div>
  );
}
