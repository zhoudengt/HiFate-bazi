type ProgressBarProps = {
  value: number;
  color?: 'gold' | 'jade' | 'red';
  label?: string;
};

const trackByColor = {
  gold: 'bg-gold/25',
  jade: 'bg-jade/25',
  red: 'bg-red/25',
} as const;

const fillByColor = {
  gold: 'bg-gold',
  jade: 'bg-jade',
  red: 'bg-red',
} as const;

export default function ProgressBar({ value, color = 'gold', label }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="w-full font-body">
      {label ? (
        <div className="mb-1 flex justify-between text-xs text-ink/80">
          <span>{label}</span>
          <span>{Math.round(clamped)}%</span>
        </div>
      ) : null}
      <div className={`h-2.5 w-full overflow-hidden rounded-full ${trackByColor[color]}`}>
        <div
          className={`h-full rounded-full ${fillByColor[color]} transition-[width] duration-300 ease-out`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
