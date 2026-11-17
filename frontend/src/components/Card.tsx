import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  // enamel plate on the wall: a hairline edge and a short, soft drop
  return <div {...rest} className={`rounded-xl bb-hard-sm bg-bb-surface p-4 ${className}`} />;
}
