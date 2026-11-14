import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { StatusBanner } from "./StatusBanner";

/** Centred 480 px mobile column (UI spec §2.3, §4.5). */
export function PageShell({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-[480px] flex-col gap-4 px-4 py-6">
      {title ? <h1 className="text-title font-semibold">{title}</h1> : null}
      {children}
    </main>
  );
}

/** Page-level error: translated message + small error code for support (UI spec §8). */
export function ErrorBanner({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  const e = error instanceof ApiError ? error : null;
  return (
    <StatusBanner tone="danger" title={t(e?.messageKey ?? "err.generic")}>
      {e && e.code !== "NETWORK" ? `${t("err.code")}: ${e.code}${e.requestId ? ` · ${e.requestId}` : ""}` : null}
    </StatusBanner>
  );
}

export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className="p-6 text-center text-bb-muted">
      {t("common.loading")}
    </p>
  );
}
