import { ArrowLeft } from "lucide-react";
import { useContext, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError } from "../api/client";
import { Logo } from "./Brand";
import { FrameContext, GuestFrame, SignBand, useSection } from "./Frame";
import { StatusBanner } from "./StatusBanner";

/** Centred 480 px mobile column (UI spec §2.3, §4.5). `back` = parent screen.
 *  Inside the owner frame the column sits between the side nav and the scene panel; outside it (login,
 *  register, choose business, not found) the screen gets the guest split-screen with the bazaar photo. */
export function PageShell({ title, back, aside, children }: {
  title?: string; back?: string; aside?: ReactNode; children: ReactNode;
}) {
  const { t } = useTranslation();
  const framed = useContext(FrameContext) !== null;
  const section = useSection();
  // A titled screen opens on a strip of the shop wall — its name painted like a signboard, the section's photo
  // behind it — and the content hangs below as enamel plates. Untitled screens (Home) start on the plates.
  const shell = (
    <>
      {!framed ? (
        <div className="bg-bb-wall px-4 pt-3 lg:hidden">
          <div className="mx-auto max-w-[480px]"><Logo to="/" /></div>
        </div>
      ) : null}
      {title || back ? (
        <SignBand section={section} photoClass={framed ? "" : "lg:hidden"}
                  className={framed ? "lg:mt-6 lg:rounded-2xl lg:bb-hard" : "lg:rounded-2xl lg:bb-hard"}>
          <div className="mx-auto flex max-w-[480px] flex-col gap-1 px-4 pb-5 pt-3 lg:max-w-none lg:px-6 lg:pb-6 lg:pt-4">
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
        </SignBand>
      ) : null}
      <main className={`bb-settle-in mx-auto flex w-full max-w-[480px] flex-col gap-4 px-4 pb-6 lg:max-w-none lg:px-0 ${title || back ? "pt-5" : "pt-6"}`}>
        {children}
      </main>
    </>
  );
  return framed ? shell : <GuestFrame section={section}>{shell}</GuestFrame>;
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
