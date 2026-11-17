import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../../api/client";
import { IconTile } from "../../components/Brand";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { DemoBadge } from "../../components/DemoBadge";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { GraphView, KIND, NodeList, pctText, type SupplyGraphData } from "../../components/SupplyGraph";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

type WhatIf = {
  node: string; exposure_pct: string | null; days: number; reason: string | null;
  result: { covered: boolean; first_shortfall: { date: string; balance_after: string; shortfall_vs_reserve: string } | null;
            min_balance_after_payment: string } | null;
};

/** Plan Ultra F4: the owner's own supply graph. Pick an area, a good, a supplier or a news item to see how much
 *  of the purchases pass through it; a shop can test "what if supply from here stops for 7 or 14 days". */
export function SupplyGraph() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [g, setG] = useState<SupplyGraphData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [w, setW] = useState<WhatIf | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<SupplyGraphData>(`/profiles/${p.id}/supply-graph`).then(setG).catch(setError);
  }, [p.id]);

  const pick = (id: string) => { setSel(id); setW(null); };
  const run = (days: number) => {
    if (!sel) return;
    setBusy(true);
    api<WhatIf>(`/profiles/${p.id}/supply-graph/whatif?node=${encodeURIComponent(sel)}&days=${days}`)
      .then(setW).catch(setError).finally(() => setBusy(false));
  };

  if (error && !g) return <PageShell title={t("graph.title")} back={`/p/${p.id}/suppliers`}><ErrorBanner error={error} /></PageShell>;
  if (!g) return <Loading />;
  const node = g.nodes.find((n) => n.id === sel) ?? null;
  const n = (v: string) => formatTaka(v, lang);

  return (
    <PageShell title={t("graph.title")} back={`/p/${p.id}/suppliers`}>
      <p className="text-bb-muted">{t("graph.intro")}</p>
      <ErrorBanner error={error} />
      <Card className="flex flex-col gap-3 overflow-hidden p-0">
        {/* scrolls sideways on a phone; focusable so a keyboard can scroll it too */}
        <div className="overflow-x-auto px-2 pt-3" tabIndex={0} role="region" aria-label={t("graph.title")}>
          <GraphView g={g} selected={sel} onSelect={pick} />
        </div>
        <p className="px-4 pb-3 text-caption text-bb-muted">{t("graph.legend")}</p>
      </Card>

      {node ? (
        <Card className="bb-settle-in flex flex-col gap-3" aria-live="polite">
          <p className="flex items-center gap-3 font-display text-card font-semibold">
            <IconTile icon={KIND[node.kind].icon} tone={KIND[node.kind].tone} />
            <span className="min-w-0">{node.is_demo ? <><DemoBadge />{" "}</> : null}{node.label}</span>
          </p>
          {node.kind === "news" && node.source_name && node.published_date ? (
            <p className="text-small text-bb-muted">
              {t("news.reported_by", { source: node.source_name, date: formatDate(node.published_date, lang) })} ·{" "}
              {t(node.corroboration === "corroborated" ? "news.corroborated" : "news.single")}
              {node.auto_collected ? ` · ${t("news.auto")}` : ""}
            </p>
          ) : null}
          <p className="font-semibold">
            {node.exposure_pct === null ? t("graph.exposure_unknown")
              : node.exposure_pct === "0.0" ? t("graph.exposure_none")
              : t("graph.exposure", { pct: pctText(node.exposure_pct, lang) })}
          </p>
          {g.whatif_available && node.kind !== "business" && node.exposure_pct !== "0.0" && node.exposure_pct !== null ? (
            <div className="flex flex-col gap-2">
              <p className="text-small">{t("graph.whatif_q")}</p>
              <div className="grid grid-cols-2 gap-3">
                {[7, 14].map((d) => (
                  <Button key={d} variant="secondary" busy={busy} onClick={() => run(d)}>{t("graph.days", { n: d })}</Button>
                ))}
              </div>
            </div>
          ) : null}
          {w && w.node === node.id ? (
            w.result ? (
              <StatusBanner tone={w.result.covered ? "success" : "warning"}
                            title={w.result.covered ? t("graph.result_ok", { days: w.days })
                              : t("graph.result_short", { days: w.days, date: formatDate(w.result.first_shortfall!.date, lang),
                                                          amount: n(w.result.first_shortfall!.shortfall_vs_reserve) })}>
                {t("scn.whatif")}
              </StatusBanner>
            ) : <StatusBanner tone="info" title={t(`graph.reason.${w.reason}`)} />
          ) : null}
        </Card>
      ) : <p className="text-small text-bb-muted">{t("graph.select_hint")}</p>}

      <NodeList g={g} selected={sel} onSelect={pick} />
      <p className="text-caption text-bb-muted">{t(`graph.basis.${g.basis}`)} · {t("graph.not_network")}</p>
    </PageShell>
  );
}
