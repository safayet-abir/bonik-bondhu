import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={`rounded-bb border border-bb-border bg-bb-surface p-4 ${className}`} />;
}
