type Choice = { text: string; id: string };

type ChoicePanelProps = {
  choices: Choice[];
  onSelect: (id: string) => void;
};

export default function ChoicePanel({ choices, onSelect }: ChoicePanelProps) {
  return (
    <div className="flex w-full flex-col gap-2 px-3 pb-[max(1rem,env(safe-area-inset-bottom))] font-body">
      {choices.map((c) => (
        <button
          key={c.id}
          type="button"
          onClick={() => onSelect(c.id)}
          className="w-full rounded-xl border border-gold/35 bg-marble/95 px-4 py-3 text-left text-ink shadow-md transition hover:border-gold/55 hover:bg-cream active:scale-[0.99]"
        >
          {c.text}
        </button>
      ))}
    </div>
  );
}
