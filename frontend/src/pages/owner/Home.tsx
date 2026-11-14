import { NotebookText } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Page, Summary, Transaction, TxnType } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { todayDhaka } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import { TXN_ICON } from "../../lib/txn";
import { useActiveProfile } from "../../state/ActiveProfile";
import { Seasons } from "../farm/Seasons";
import { EntryRow } from "./Entries";

type Data = { today: Summary; month: Summary; recent: Transaction[] };
const QUICK: TxnType[] = ["sale_cash", "sale_credit", "purchase_cash", "operating_expense"];

/** /p/:pid/home — shop home (SCR-O03) or farm home (SCR-F01). */
export function ProfileHome() {
  return useActiveProfile().activity_type === "crop_farm" ? <Seasons /> : <Home />;
}

function InOut({ title, s, lang }: { title: string; s: Summary; lang: Lang }) {
  const { t } = useTranslation();
  return (
    <Card className="flex flex-col gap-2 p-3">
      <p className="text-small font-semibold text-bb-muted">{title}</p>
      {/* Label above amount: fits 360 px screens without awkward wrapping */}
      <p className="flex flex-col">
        <span className="text-small">{t("home.cash_in")}</span>
        <span className="tabular text-card font-semibold whitespace-nowrap text-bb-success">
          {formatTaka(s.operating_cash_in, lang)}
        </span>
      </p>
      <p className="flex flex-col">
        <span className="text-small">{t("home.cash_out")}</span>
        <span className="tabular text-card font-semibold whitespace-nowrap">{formatTaka(s.operating_cash_out, lang)}</span>
      </p>
    </Card>
  );
}

/** SCR-O03 Shop home. First-time: Path A "Record my money" (Path B
 *  "Check financing" appears in P3 when its endpoints exist). Returning:
 *  today / this month, quick add, recent entries (tap → detail / void). */
export function Home() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const today = todayDhaka();
    Promise.all([
      api<Summary>(`/profiles/${p.id}/summary?from=${today}&to=${today}`),
      api<Summary>(`/profiles/${p.id}/summary`),
      api<Page<Transaction>>(`/profiles/${p.id}/transactions?limit=5`),
    ])
      .then(([todayS, month, recent]) => setData({ today: todayS, month, recent: recent.items }))
      .catch(setError);
  }, [p.id]);

  if (error) return <PageShell><ErrorBanner error={error} /></PageShell>;
  if (!data) return <Loading />;

  const add = (type: TxnType) => navigate(`/p/${p.id}/entries/new?type=${type}`);

  if (data.recent.length === 0) {
    return (
      <PageShell title={t("home.welcome")}>
        <p className="text-bb-muted">{t("home.what_to_do")}</p>
        <button type="button" onClick={() => add("sale_cash")}
                className="flex flex-col items-start gap-1 rounded-bb border border-bb-border bg-bb-surface p-4 text-left">
          <span className="flex items-center gap-2 text-card font-semibold">
            <NotebookText aria-hidden className="size-6 text-bb-primary" />
            {t("home.path_a")}
          </span>
          <span className="text-small text-bb-muted">{t("home.path_a_hint")}</span>
        </button>
      </PageShell>
    );
  }

  return (
    <PageShell>
      {notice ? <StatusBanner tone="success" title={t(notice)} /> : null}
      <div className="grid grid-cols-2 gap-3">
        <InOut title={t("period.today")} s={data.today} lang={lang} />
        <InOut title={t("period.this_month")} s={data.month} lang={lang} />
      </div>
      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">{t("home.quick_add")}</h2>
        <div className="grid grid-cols-2 gap-3">
          {QUICK.map((ty) => {
            const Icon = TXN_ICON[ty];
            return (
              <Button key={ty} variant="secondary" onClick={() => add(ty)}
                      icon={<Icon aria-hidden className={`size-5 ${ty === "sale_cash" ? "text-bb-success" : ""}`} />}>
                {t(`txn.${ty}`)}
              </Button>
            );
          })}
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">{t("home.recent")}</h2>
        <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
          {data.recent.map((tx) => <EntryRow key={tx.id} tx={tx} to={`/p/${p.id}/entries/${tx.id}`} />)}
        </ul>
        <Link to={`/p/${p.id}/summary`} className="text-center font-semibold text-bb-primary underline">
          {t("home.see_summary")}
        </Link>
      </section>
    </PageShell>
  );
}
