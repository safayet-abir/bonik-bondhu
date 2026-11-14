import { BarChart3, CheckCircle2, Pencil, PlusCircle, Trash2, Wheat } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { CostItem, Page, SeasonDetail as SeasonDetailT, SeasonSummary, Transaction } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatNumber, formatTaka } from "../../lib/format";
import { FARM_COST_CATEGORIES } from "../../lib/txn";
import { useActiveProfile } from "../../state/ActiveProfile";
import { seasonTitle } from "../owner/AddEntry";
import { EntryRow } from "../owner/Entries";
import { areaText, StatusChip } from "./Seasons";

const PRICE_SOURCES = ["owner_estimate", "supplier_quote", "own_purchase_history", "reference_market_price", "public_listing"];

function CostItemForm({ sid, onSaved, onCancel }: { sid: string; onSaved: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const [category, setCategory] = useState("seed");
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [source, setSource] = useState("owner_estimate");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    try {
      await api(`/profiles/${p.id}/seasons/${sid}/cost-items`, {
        method: "POST",
        body: { category, item_name: name || t(`category.${category}`), quantity, unit: unit || t("season.unit_lot"),
                unit_cost: unitCost, price_source_type: source },
      });
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
        <ErrorBanner error={error} />
        <SelectField label={t("season.cost_category")} value={category} onChange={setCategory}
                     options={FARM_COST_CATEGORIES.map((c) => ({ value: c, label: t(`category.${c}`) }))} />
        <Field label={t("season.item_name")} value={name} maxLength={80} hint={t("season.item_name_hint")}
               onChange={(e) => setName(e.target.value)} errorKey={fields.item_name} />
        <div className="grid grid-cols-2 gap-3">
          <AmountInput label={t("season.quantity")} value={quantity} onChange={setQuantity} errorKey={fields.quantity} />
          <Field label={t("season.unit_name")} value={unit} maxLength={20} hint={t("season.unit_name_hint")}
                 onChange={(e) => setUnit(e.target.value)} errorKey={fields.unit} />
        </div>
        <AmountInput label={t("season.unit_cost")} value={unitCost} onChange={setUnitCost} errorKey={fields.unit_cost} />
        <SelectField label={t("price_source.label")} value={source} onChange={setSource}
                     options={PRICE_SOURCES.map((s) => ({ value: s, label: t(`price_source.${s}`) }))} />
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>
          <Button type="submit" busy={busy}>{t("common.save")}</Button>
        </div>
      </form>
    </Card>
  );
}

/** SCR-F03 Season costs & sales: the plan (cost items with a "Paid" button
 *  that opens SCR-O04 pre-filled) and the actual ledger entries (DEC-27). */
export function SeasonDetail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const { sid } = useParams();
  const navigate = useNavigate();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const [season, setSeason] = useState<SeasonDetailT | null>(null);
  const [summary, setSummary] = useState<SeasonSummary | null>(null);
  const [entries, setEntries] = useState<Transaction[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [adding, setAdding] = useState(false);

  const base = `/p/${p.id}/seasons/${sid}`;
  const load = useCallback(() => {
    Promise.all([
      api<SeasonDetailT>(`/profiles/${p.id}/seasons/${sid}`),
      api<SeasonSummary>(`/profiles/${p.id}/seasons/${sid}/summary`),
      api<Page<Transaction>>(`/profiles/${p.id}/transactions?season_id=${sid}&limit=200`),
    ]).then(([s, sum, tx]) => { setSeason(s); setSummary(sum); setEntries(tx.items); }).catch(setError);
  }, [p.id, sid]);
  useEffect(load, [load]);

  async function remove(item: CostItem) {
    try {
      await api(`/profiles/${p.id}/seasons/${sid}/cost-items/${item.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err);
    }
  }

  function paid(item: CostItem) {
    const remaining = (Number(item.total_cost) - Number(item.paid_total)).toFixed(2); // prefill only; editable
    const q = new URLSearchParams({
      type: "purchase_cash", season_id: sid ?? "", cost_item_id: item.id, category: item.category,
      item_name: item.item_name, back: base,
      ...(Number(remaining) > 0 ? { amount: remaining.replace(/\.00$/, "") } : {}),
    });
    void navigate(`/p/${p.id}/entries/new?${q}`);
  }

  if (!season || !summary) return <PageShell back={`/p/${p.id}/home`}><ErrorBanner error={error} />{error ? null : <Loading />}</PageShell>;

  return (
    <PageShell title={seasonTitle(season, t)} back={`/p/${p.id}/home`}>
      {notice ? <StatusBanner tone="success" title={t(notice)} /> : null}
      <ErrorBanner error={error} />
      <div className="flex items-center justify-between gap-2">
        <p className="text-small text-bb-muted">{areaText(season, t, lang)}</p>
        <StatusChip status={season.status} />
      </div>
      <Card className="grid grid-cols-3 gap-2 text-center">
        {([["season.planned_cost", summary.planned_cost_total], ["season.paid_cost", summary.paid_cost_total],
           ["season.sales", summary.actual_sales_total]] as const).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <span className="text-caption text-bb-muted">{t(k)}</span>
            <span className="tabular font-semibold">{formatTaka(v, lang)}</span>
          </div>
        ))}
      </Card>
      <div className="grid grid-cols-2 gap-3">
        <Button variant="secondary" icon={<BarChart3 aria-hidden className="size-5" />} onClick={() => navigate(`${base}/summary`)}>
          {t("season.summary")}
        </Button>
        <Button variant="secondary" icon={<Pencil aria-hidden className="size-5" />} onClick={() => navigate(`${base}/edit`)}>
          {t("common.edit")}
        </Button>
      </div>

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">{t("season.plan")}</h2>
        {season.cost_items.length === 0 ? <p className="text-small text-bb-muted">{t("season.plan_empty")}</p> : null}
        {season.cost_items.length > 0 ? (
          <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
            {season.cost_items.map((i) => {
              const fullyPaid = Number(i.paid_total) >= Number(i.total_cost) && Number(i.total_cost) > 0;
              return (
                <li key={i.id} className="flex flex-col gap-1 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span>
                      <span className="block font-semibold">{i.item_name}</span>
                      <span className="text-small text-bb-muted">
                        {formatNumber(i.quantity, lang)} {i.unit} × {formatTaka(i.unit_cost, lang)} · {t(`price_source.${i.price_source_type}`)}
                      </span>
                    </span>
                    <span className="tabular font-semibold whitespace-nowrap">{formatTaka(i.total_cost, lang)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-small">
                      {fullyPaid ? (
                        <span className="flex items-center gap-1 font-semibold text-bb-success">
                          <CheckCircle2 aria-hidden className="size-4" />{t("season.paid_done")}
                        </span>
                      ) : t("season.paid_so_far", { amount: formatTaka(i.paid_total, lang) })}
                    </span>
                    <span className="flex items-center">
                      {Number(i.paid_total) === 0 ? (
                        <button type="button" onClick={() => void remove(i)} aria-label={t("common.delete")}
                                className="flex min-h-12 min-w-12 items-center justify-center text-bb-muted">
                          <Trash2 aria-hidden className="size-5" />
                        </button>
                      ) : null}
                      {!fullyPaid ? (
                        <Button variant="secondary" onClick={() => paid(i)}>{t("season.mark_paid")}</Button>
                      ) : null}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : null}
        {adding ? (
          <CostItemForm sid={sid!} onSaved={() => { setAdding(false); load(); }} onCancel={() => setAdding(false)} />
        ) : (
          <Button variant="secondary" full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => setAdding(true)}>
            {t("season.add_cost")}
          </Button>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">{t("season.actual")}</h2>
        {entries.length === 0 ? <p className="text-small text-bb-muted">{t("season.actual_empty")}</p> : (
          <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
            {entries.map((tx) => <EntryRow key={tx.id} tx={tx} to={`/p/${p.id}/entries/${tx.id}`} />)}
          </ul>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Button variant="secondary" onClick={() => navigate(`/p/${p.id}/entries/new?type=sale_cash&season_id=${sid}&back=${base}`)}>
            {t("season.record_sale")}
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/p/${p.id}/entries/new?type=operating_expense&season_id=${sid}&back=${base}`)}>
            {t("season.record_cost")}
          </Button>
        </div>
      </section>

      {season.status !== "harvested" ? (
        <Button full icon={<Wheat aria-hidden className="size-5" />} onClick={() => navigate(`${base}/harvest`)}>
          {t("season.record_harvest")}
        </Button>
      ) : (
        <Card className="text-small">
          {t("season.harvested_on", {
            date: season.actual_harvest_date ? formatDate(season.actual_harvest_date, lang) : "",
            kg: formatNumber(season.actual_output ?? "0", lang),
          })}
        </Card>
      )}
      <Link to={`/p/${p.id}/entries`} className="text-center text-small font-semibold text-bb-primary underline">
        {t("entries.title")}
      </Link>
    </PageShell>
  );
}
