import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError } from "../api/client";
import { StatusBanner } from "./StatusBanner";

/** Centred 480 px mobile column (UI spec §2.3, §4.5). `back` = parent screen. */
export function PageShell({ title, back, children }: { title?: string; back?: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <main className="bb-settle-in mx-auto flex w-full max-w-[480px] flex-col gap-4 px-4 py-6">
      {back ? (
        <Link to={back} className="-mb-2 flex min-h-12 items-center gap-1 self-start text-bb-primary">
          <ArrowLeft aria-hidden className="size-5" />
          {t("common.back")}
        </Link>
      ) : null}
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
