import type { TFunction } from "i18next";
import { CalendarDays, PlusCircle, Sprout } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Page, Season, SeasonSummary } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatNumber, formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";
import { seasonTitle } from "../owner/AddEntry";

export function areaText(s: Season, t: TFunction, lang: Lang): string {
  const acres = t("season.acres", { n: formatNumber(s.area_acres, lang) });
  if (s.area_unit === "acre") return acres;
  return `${acres} (${formatNumber(s.area_value, lang)} ${t(`season.unit.${s.area_unit}`)})`;
}

export function StatusChip({ status }: { status: Season["status"] }) {
  const { t } = useTranslation();
  const tone = status === "harvested" ? "bg-bb-success text-white" : status === "growing" ? "bg-bb-primary-soft text-bb-primary" : "bg-bb-bg text-bb-muted";
  return <span className={`rounded-full px-3 py-0.5 text-caption font-semibold ${tone}`}>{t(`season.status.${status}`)}</span>;
}

/** SCR-F01 Farm home: season cards. Farmers are never asked for daily
 *  entries and never see a forecast (FR-SEA-08). */
export function Seasons() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const [items, setItems] = useState<SeasonSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<Page<Season>>(`/profiles/${p.id}/seasons`)
      .then((r) => Promise.all(r.items.map((s) => api<SeasonSummary>(`/profiles/${p.id}/seasons/${s.id}/summary`))))
      .then(setItems)
      .catch(setError);
  }, [p.id]);

  return (
    <PageShell title={t("season.title")}>
      {notice ? <StatusBanner tone="success" title={t(notice)} /> : null}
      <Button full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => navigate(`/p/${p.id}/seasons/new`)}>
        {t("season.new")}
      </Button>
      <ErrorBanner error={error} />
      {!items && !error ? <Loading /> : null}
      {items && items.length === 0 ? (
        <EmptyState icon={<Sprout className="size-10" />} message={t("season.empty")} />
      ) : null}
      {items?.map(({ season: s, planned_cost_total, paid_cost_total }) => (
        <Link key={s.id} to={`/p/${p.id}/seasons/${s.id}`}>
          <Card className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <p className="flex items-center gap-2 font-semibold">
                <Sprout aria-hidden className="size-5 text-bb-primary" />
                {seasonTitle(s, t)}
              </p>
              <StatusChip status={s.status} />
            </div>
            <p className="text-small text-bb-muted">{areaText(s, t, lang)}</p>
            <div className="grid grid-cols-2 gap-1 text-small">
              <span className="text-bb-muted">{t("season.planned_cost")}</span>
              <span className="tabular text-right">{formatTaka(planned_cost_total, lang)}</span>
              <span className="text-bb-muted">{t("season.paid_cost")}</span>
              <span className="tabular text-right">{formatTaka(paid_cost_total, lang)}</span>
            </div>
            <p className="flex items-center gap-1 text-small text-bb-muted">
              <CalendarDays aria-hidden className="size-4" />
              {t("season.harvest_on", { date: formatDate(s.expected_harvest_date, lang) })}
            </p>
          </Card>
        </Link>
      ))}
    </PageShell>
  );
}
