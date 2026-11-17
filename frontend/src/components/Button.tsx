import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger";

// every button is a block with the iron edge; pressing pushes it into its shadow (design round 3)
const VARIANTS: Record<Variant, string> = {
  primary: "bb-hard-sm bg-bb-primary text-white hover:bg-bb-primary-dark disabled:opacity-60",
  secondary: "bb-hard-sm bg-bb-surface text-bb-primary hover:bg-bb-primary-soft disabled:opacity-60",
  danger: "bb-hard-sm bg-bb-danger text-white disabled:opacity-60",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: ReactNode;
  busy?: boolean;
  full?: boolean;
};

/** Verb label + optional icon (icons never replace text, UI spec §1.4).
 *  `busy` disables the button to prevent double submit (UI spec §8). */
export function Button({ variant = "primary", icon, busy, full, disabled, className = "", children, ...rest }: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 font-semibold transition-[transform,box-shadow] duration-100 enabled:active:translate-x-0.5 enabled:active:translate-y-0.5 enabled:active:shadow-none ${
        full ? "w-full" : ""
      } ${VARIANTS[variant]} ${className}`}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
