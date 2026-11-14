import { LogIn, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { getHealth, type Health } from "../../api/client";
import { Button } from "../../components/Button";
import { LanguageSwitch } from "../../components/LanguageSwitch";

/** SCR-A01 Welcome + language (UI spec §6). Shows server status from /health
 *  (P0 Definition of Done: the welcome screen talks to /health). */
export function Welcome() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [health, setHealth] = useState<Health | "error" | null>(null);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setHealth("error"));
    return () => {
      alive = false;
    };
  }, []);

  const statusText =
    health === null ? t("system.checking")
    : health === "error" ? t("err.network")
    : health.db === "ok" ? t("system.ok")
    : t("system.degraded");
  const statusOk = health !== null && health !== "error" && health.db === "ok";

  return (
    <main className="mx-auto flex min-h-dvh max-w-[480px] flex-col justify-between gap-8 px-4 py-10">
      <div className="flex flex-col items-center gap-2 pt-8 text-center">
        <h1 className="text-amount font-semibold text-bb-primary-dark" lang="bn">
          বণিক বন্ধু
        </h1>
        <p className="text-card font-semibold" lang="en">
          Bonik Bondhu
        </p>
        <p className="text-bb-muted">{t("app.tagline")}</p>
      </div>

      <section className="flex flex-col items-center gap-3">
        <p className="font-semibold">
          {t("lang.label")} / Language
        </p>
        <LanguageSwitch large />
      </section>

      <div className="flex flex-col gap-3">
        <Button full icon={<UserPlus aria-hidden className="size-5" />} onClick={() => navigate("/register")}>
          {t("welcome.create_account")}
        </Button>
        <Button
          full
          variant="secondary"
          icon={<LogIn aria-hidden className="size-5" />}
          onClick={() => navigate("/login")}
        >
          {t("welcome.login")}
        </Button>
        <p className="mt-2 flex items-center justify-center gap-2 text-caption text-bb-muted" aria-live="polite">
          <span
            aria-hidden
            className={`inline-block size-2 rounded-full ${statusOk ? "bg-bb-success" : "bg-bb-warning"}`}
          />
          {t("system.status")}: {statusText}
        </p>
      </div>
    </main>
  );
}
