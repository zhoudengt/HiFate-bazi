export default function Loading() {
  return (
    <div className="flex min-h-[120px] w-full items-center justify-center font-body" role="status" aria-live="polite">
      <div className="relative h-14 w-14">
        <div
          className="absolute inset-0 animate-spin rounded-full border-2 border-gold/25 border-t-gold border-r-gold/60"
          aria-hidden
        />
        <svg
          className="absolute inset-[18%] animate-[spin_3s_linear_infinite_reverse] text-gold"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden
        >
          <path d="M12 2a10 10 0 0110 10h-3a7 7 0 00-7-7V2z" opacity="0.95" />
          <path d="M12 22a10 10 0 01-10-10h3a7 7 0 007 7v3z" opacity="0.55" />
        </svg>
      </div>
      <span className="sr-only">加载中</span>
    </div>
  );
}
