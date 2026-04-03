export function formatPoints(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

/** 顶栏命运点数等 HUD：162000 → 162K（与参考稿一致） */
export function formatCompactHudNumber(n: number): string {
  const v = Math.trunc(n);
  if (v >= 1_000_000) {
    const m = v / 1_000_000;
    const s = m >= 10 ? m.toFixed(0) : m.toFixed(1);
    return `${s.replace(/\.0$/, '')}M`;
  }
  if (v >= 1000) {
    const k = v / 1000;
    const s = k >= 100 ? k.toFixed(0) : k >= 10 ? k.toFixed(0) : k.toFixed(1);
    return `${s.replace(/\.0$/, '')}K`;
  }
  return String(v);
}

export function formatDate(d: string | Date): string {
  const date = typeof d === 'string' ? new Date(d) : d;
  return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' });
}
