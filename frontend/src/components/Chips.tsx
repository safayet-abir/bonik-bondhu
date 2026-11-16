type Props<T extends string> = {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
};

/** Single-choice toggle chips (period, filters, season name, frequency). */
export function Chips<T extends string>({ label, value, options, onChange }: Props<T>) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}
                className={`min-h-12 rounded-full border px-4 transition-colors duration-150 ${
                  value === o.value
                    ? "border-bb-wall bg-bb-wall font-semibold text-white"
                    : "border-bb-border bg-bb-surface hover:border-bb-wall"
                }`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
