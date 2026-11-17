import { Inbox } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api } from "../../api/client";
import type { LenderCase, Page } from "../../api/types";
import { Chips } from "../../components/Chips";
import { DemoBadge } from "../../components/DemoBadge";
import { EmptyState } from "../../components/EmptyState";
import { ErrorBanner, Loading } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { STATUS_KEY } from "../../lib/financing";
import { formatTaka } from "../../lib/format";
import { LenderShell } from "./LenderShell";

type Tab = "all" | "pending" | "active" | "closed";

/** SCR-L01 case list. Pending cases show no applicant until the owner approves. */
export function Cases() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const [tab, setTab] = useState<Tab>("all");
  const [cases, setCases] = useState<LenderCase[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setCases(null);
    api<Page<LenderCase>>(`/lender/cases${tab === "all" ? "" : `?status=${tab}`}`)
      .then((r) => setCases(r.items)).catch(setError);
  }, [tab]);

  const day = (iso: string | null) => (iso ? formatDate(iso.slice(0, 10), lang) : "—");
  return (
    <LenderShell title={t("lender.cases")}>
      <Chips label={t("lender.cases")} value={tab} onChange={setTab}
             options={(["all", "pending", "active", "closed"] as Tab[]).map((v) => ({ value: v, label: t(`lender.tab.${v}`) }))} />
      <ErrorBanner error={error} />
      {!cases && !error ? <Loading /> : null}
      {cases && cases.length === 0 ? <EmptyState icon={<Inbox className="size-10" />} message={t("lender.no_cases")} /> : null}
      {cases && cases.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bb-hard-sm bg-bb-surface">
          <table className="w-full min-w-[720px] text-left">
            <thead className="text-small text-bb-muted">
              <tr>
                <th className="p-3">{t("lender.applicant")}</th>
                <th className="p-3">{t("lender.amount")}</th>
                <th className="p-3">{t("lender.check_status")}</th>
                <th className="p-3">{t("lender.status")}</th>
                <th className="p-3">{t("lender.valid_until")}</th>
                <th className="p-3">{t("lender.review")}</th>
                <th className="p-3">{t("lender.last_viewed")}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const readable = c.status === "approved" && !c.is_expired;
                return (
                  <tr key={c.consent_id} className="border-t border-bb-border">
                    <td className="p-3">
                      {c.applicant ? (
                        readable ? (
                          <Link to={`/lender/cases/${c.consent_id}`} className="font-semibold text-bb-primary underline">
                            {c.applicant.display_name}
                          </Link>
                        ) : <span className="font-semibold">{c.applicant.display_name}</span>
                      ) : <span className="text-bb-muted">{t("lender.awaiting_owner")}</span>}
                      {c.applicant?.is_demo ? <> <DemoBadge /></> : null}
                      {c.applicant ? <span className="block text-small text-bb-muted">{t(`profile.type.${c.applicant.activity_type}`)}</span> : null}
                    </td>
                    <td className="tabular p-3">{c.requested_amount ? formatTaka(c.requested_amount, lang) : "—"}</td>
                    <td className="p-3 text-small">{c.assessment_status ? t(STATUS_KEY[c.assessment_status]) : "—"}</td>
                    <td className="p-3">{t(`consent.status.${c.is_expired ? "expired" : c.status}`)}</td>
                    <td className="p-3">{day(c.valid_until)}</td>
                    <td className="p-3 text-small">
                      {c.decision ? t(`decision.${c.decision}`) : c.review_status ? t(`review.${c.review_status}`) : "—"}
                    </td>
                    <td className="p-3 text-small">{day(c.last_read_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </LenderShell>
  );
}
