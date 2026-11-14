import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-bb-primary text-white active:bg-bb-primary-dark disabled:opacity-60",
  secondary: "bg-bb-surface text-bb-primary border border-bb-primary active:bg-bb-primary-soft disabled:opacity-60",
  danger: "bg-bb-danger text-white disabled:opacity-60",
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
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-bb px-4 font-semibold ${
        full ? "w-full" : ""
      } ${VARIANTS[variant]} ${className}`}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
