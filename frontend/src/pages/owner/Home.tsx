import { HandCoins, NotebookText, TrendingUp } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Page, Summary, Transaction, TxnType } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EconomyCard } from "../../components/Economy";
import { Balance } from "../../components/Balance";
import { LedgerScene } from "../../components/Scenes";
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

/** Farm profiles never get a forecast screen (FR-SEA-08). */
export function ShopOnly({ children }: { children: ReactNode }) {
  const p = useActiveProfile();
  return p.activity_type === "shop" ? <>{children}</> : <Navigate to={`/p/${p.id}/home`} replace />;
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

/** SCR-O03 Shop home. First-time: Path A "Record my money" or Path B
 *  "Check financing". Returning: today / this month, quick add, recent
 *  entries (tap → detail / void), forecast and financing shortcuts. */
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
        {/* two doors, each with its own scene from the counter: the ledger, and the balance */}
        {[
          { key: "a", onClick: () => add("sale_cash"), icon: NotebookText, scene: <LedgerScene /> },
          { key: "b", onClick: () => navigate(`/p/${p.id}/financing/new`), icon: HandCoins,
            scene: <div className="mx-auto w-[62%]"><Balance left={12} right={10} settleFrom={10} label={t("home.path_b")} /></div> },
        ].map(({ key, onClick, icon: Icon, scene }, i) => (
          <button key={key} type="button" onClick={onClick} style={{ animationDelay: `${i * 90}ms` }}
                  className="bb-settle-in group flex flex-col overflow-hidden rounded-bb border border-bb-border bg-bb-surface text-left shadow-[0_2px_8px_-4px_rgb(20_32_29/0.18)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-px">
            <span className="block bg-bb-wall px-4 pt-3">{scene}</span>
            <span className="flex flex-col gap-1 p-4">
              <span className="flex items-center gap-2 font-display text-card font-semibold">
                <Icon aria-hidden className="size-6 text-bb-primary" />
                {t(`home.path_${key}`)}
              </span>
              <span className="text-small text-bb-muted">{t(`home.path_${key}_hint`)}</span>
            </span>
          </button>
        ))}
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
      <div className="grid grid-cols-2 gap-3">
        <Button variant="secondary" icon={<TrendingUp aria-hidden className="size-5" />}
                onClick={() => navigate(`/p/${p.id}/forecast`)}>
          {t("forecast.title")}
        </Button>
        <Button variant="secondary" icon={<HandCoins aria-hidden className="size-5" />}
                onClick={() => navigate(`/p/${p.id}/financing`)}>
          {t("home.path_b")}
        </Button>
      </div>
      <EconomyCard />
    </PageShell>
  );
}
