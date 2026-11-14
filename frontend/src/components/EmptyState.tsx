import type { ReactNode } from "react";

/** Icon + one-line explanation + one primary action — never a blank card (UI spec §8). */
export function EmptyState({ icon, message, action }: { icon: ReactNode; message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-bb border border-dashed border-bb-border bg-bb-surface p-6 text-center">
      <div aria-hidden className="text-bb-muted">
        {icon}
      </div>
      <p>{message}</p>
      {action}
    </div>
  );
}
