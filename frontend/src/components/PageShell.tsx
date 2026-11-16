import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError } from "../api/client";
import { StatusBanner } from "./StatusBanner";

/** Centred 480 px mobile column (UI spec §2.3, §4.5). `back` = parent screen. */
export function PageShell({ title, back, aside, children }: {
  title?: string; back?: string; aside?: ReactNode; children: ReactNode;
}) {
  const { t } = useTranslation();
  // A titled screen opens on a strip of the shop wall — its name painted like a signboard — and the content
  // hangs below as enamel plates (world "Daripalla"). Untitled screens (Home) start straight on the plates.
  return (
    <>
      {title || back ? (
        <div className="bg-bb-wall text-white">
          <div className="mx-auto flex max-w-[480px] flex-col gap-1 px-4 pb-5 pt-3">
            {back ? (
              <Link to={back} className="-ml-1 flex min-h-12 items-center gap-1 self-start px-1 text-[#d6ece8] hover:text-white">
                <ArrowLeft aria-hidden className="size-5" />
                {t("common.back")}
              </Link>
            ) : null}
            <div className="flex flex-wrap items-center justify-between gap-3">
              {title ? <h1 className="text-[1.6rem] font-semibold leading-tight">{title}</h1> : null}
              {aside}
            </div>
          </div>
        </div>
      ) : null}
      <main className={`bb-settle-in mx-auto flex w-full max-w-[480px] flex-col gap-4 px-4 pb-6 ${title || back ? "pt-5" : "pt-6"}`}>
        {children}
      </main>
    </>
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
