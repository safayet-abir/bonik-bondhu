import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

type Tone = "success" | "warning" | "danger" | "info";

const TONES: Record<Tone, { cls: string; Icon: typeof Info }> = {
  success: { cls: "border-bb-success text-bb-success", Icon: CheckCircle2 },
  warning: { cls: "border-bb-warning text-bb-warning", Icon: AlertTriangle },
  danger: { cls: "border-bb-danger text-bb-danger", Icon: XCircle },
  info: { cls: "border-bb-info text-bb-info", Icon: Info },
};

/** Status = icon + colour + words, never colour alone (UI spec §2.1, §9). */
export function StatusBanner({ tone, title, children }: { tone: Tone; title: string; children?: ReactNode }) {
  const { cls, Icon } = TONES[tone];
  return (
    <div role="status" className={`flex gap-3 rounded-bb border bg-bb-surface p-3 shadow-[0_2px_8px_-4px_rgb(20_32_29/0.18)] ${cls}`}>
      <Icon aria-hidden className="mt-1 size-5 shrink-0" />
      <div className="text-bb-text">
        <p className="font-semibold">{title}</p>
        {children ? <div className="text-small text-bb-muted">{children}</div> : null}
      </div>
    </div>
  );
}
