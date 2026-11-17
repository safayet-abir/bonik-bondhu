import type { ReactNode } from "react";

/** Icon + one-line explanation + one primary action — never a blank card (UI spec §8). */
export function EmptyState({ icon, message, action }: { icon: ReactNode; message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl bb-hard-sm bg-bb-surface p-6 text-center">
      {/* the icon sits on a disc of the shop wall, drawn in brass */}
      <div aria-hidden className="flex size-20 items-center justify-center rounded-full bg-bb-wall text-bb-brass">
        {icon}
      </div>
      <p>{message}</p>
      {action}
    </div>
  );
}
