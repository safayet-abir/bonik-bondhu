import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  // enamel plate on the wall: a hairline edge and a short, soft drop
  return <div {...rest} className={`rounded-bb border border-bb-border bg-bb-surface p-4 shadow-[0_2px_8px_-4px_rgb(20_32_29/0.18)] ${className}`} />;
}
