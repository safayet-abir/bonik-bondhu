import { ChevronRight, HandCoins, PlusCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { FinancingRequest, Page } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { STATUS_KEY } from "../../lib/financing";
import { formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

/** Financing tab: the owner's requests, each opening its latest result or
 *  the wizard step where it stopped. */
export function Financing() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [items, setItems] = useState<FinancingRequest[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<Page<FinancingRequest>>(`/profiles/${p.id}/financing-requests`).then((r) => setItems(r.items)).catch(setError);
  }, [p.id]);

  const base = `/p/${p.id}`;
  return (
    <PageShell title={t("fin.title")}>
      <ErrorBanner error={error} />
      <p className="text-small text-bb-muted">{t("fin.intro")}</p>
      <Button full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => navigate(`${base}/financing/new`)}>
        {t("fin.new")}
      </Button>
      {!items && !error ? <Loading /> : null}
      {items && items.length > 0 ? (
        <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
          {items.map((r) => {
            const a = r.latest_assessment;
            const to = a && !a.is_stale ? `${base}/assessment/${a.id}` : `${base}/financing/${r.id}/step/${a ? 5 : 2}`;
            return (
              <li key={r.id}>
                <Link to={to} className="flex min-h-16 items-center gap-3 px-4 py-3">
                  <HandCoins aria-hidden className="size-5 text-bb-primary" />
                  <div className="flex flex-1 flex-col">
                    <span className="font-semibold">{formatTaka(r.requested_amount, lang)} · {t(`fin.cat.${r.purpose_category}`)}</span>
                    <span className="line-clamp-1 text-small text-bb-muted">{r.purpose_text}</span>
                    <span className="text-caption">
                      {a ? (a.is_stale ? t("asm.stale") : t(STATUS_KEY[a.status])) : t("fin.not_checked")}
                    </span>
                  </div>
                  <ChevronRight aria-hidden className="size-5 text-bb-muted" />
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </PageShell>
  );
}
