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
                className={`min-h-12 rounded-full border px-4 ${
                  value === o.value
                    ? "border-bb-primary bg-bb-primary-soft font-semibold text-bb-primary"
                    : "border-bb-border bg-bb-surface"
                }`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
