import type { TFunction } from "i18next";
import { Info } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { Debt, DebtList, Page, Season, Supplier, TxnType } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { addDays, formatDate, todayDhaka } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import {
  COST_ITEM_TYPES, FARM_COST_CATEGORIES, LOAN_TYPES, SHOP_EXPENSE_CATEGORIES, SUPPLIER_TYPES, TXN_GROUPS, TXN_ICON,
} from "../../lib/txn";
import { useActiveProfile } from "../../state/ActiveProfile";

const ALL_TYPES = TXN_GROUPS.flatMap((g) => g.types);
type Duplicate = { amount: string; value_date: string };

/** SCR-O04 Add entry (FR-LED-01..07). One client_request_id per form
 *  instance makes a double tap or retry save only once (FR-LED-10).
 *  Query params pre-fill it from other screens, e.g. a season cost item's
 *  "Paid" button: ?type=purchase_cash&season_id=…&cost_item_id=…&amount=… */
export function AddEntry() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const isFarm = p.activity_type === "crop_farm";
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const qType = params.get("type") as TxnType | null;
  const costItemId = params.get("cost_item_id");
  const back = params.get("back");

  const requestId = useMemo(() => crypto.randomUUID(), []);
  const today = todayDhaka();
  const [type, setType] = useState<TxnType>(qType && ALL_TYPES.includes(qType) ? qType : "sale_cash");
  const [amount, setAmount] = useState(params.get("amount") ?? "");
  const [date, setDate] = useState(today);
  const categories = isFarm ? FARM_COST_CATEGORIES : SHOP_EXPENSE_CATEGORIES;
  const [category, setCategory] = useState(params.get("category") ?? (isFarm ? "" : "rent"));
  const [note, setNote] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [debtId, setDebtId] = useState("");
  const [seasonId, setSeasonId] = useState(params.get("season_id") ?? "");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [duplicate, setDuplicate] = useState<Duplicate | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Page<Supplier>>(`/profiles/${p.id}/suppliers`).then((r) => setSuppliers(r.items.filter((s) => s.is_active)))
      .catch(() => setSuppliers([]));
    api<DebtList>(`/profiles/${p.id}/debts`).then((r) => setDebts(r.items.filter((d) => d.status === "active")))
      .catch(() => setDebts([]));
    if (isFarm) api<Page<Season>>(`/profiles/${p.id}/seasons`).then((r) => setSeasons(r.items)).catch(() => setSeasons([]));
  }, [p.id, isFarm]);

  const showSupplier = SUPPLIER_TYPES.includes(type);
  const showDebt = LOAN_TYPES.includes(type);
  const showCategory = type === "operating_expense" || (isFarm && COST_ITEM_TYPES.includes(type));
  const linkCostItem = costItemId && COST_ITEM_TYPES.includes(type) ? costItemId : null;

  function pick(ty: TxnType) {
    setType(ty);
    setDuplicate(null);
  }

  async function save(confirmDuplicate: boolean) {
    setBusy(true);
    setFields({});
    setError(null);
    try {
      await api(`/profiles/${p.id}/transactions`, {
        method: "POST",
        body: {
          txn_type: type, amount, value_date: date, note: note || null,
          category: showCategory && category ? category : null,
          supplier_id: showSupplier && supplierId ? supplierId : null,
          debt_facility_id: showDebt && debtId ? debtId : null,
          season_id: isFarm && seasonId ? seasonId : null,
          season_cost_item_id: linkCostItem,
          client_request_id: requestId,
          confirm_duplicate: confirmDuplicate,
        },
      });
      void navigate(back ?? `/p/${p.id}/home`, { state: { notice: "entry.saved" } });
    } catch (err) {
      if (err instanceof ApiError && err.code === "POSSIBLE_DUPLICATE") {
        setDuplicate(err.details.existing as Duplicate);
      } else if (err instanceof ApiError && Object.keys(err.fields).length) {
        setFields(err.fields);
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!amount || Number(amount) <= 0) {
      setFields({ amount: "entry.err.amount" });
      return;
    }
    setDuplicate(null);
    void save(false);
  }

  return (
    <PageShell title={t("entry.new")} back={back ?? undefined}>
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1 font-semibold">{t("entry.what_happened")}</legend>
          {TXN_GROUPS.map((g) => (
            <div key={g.key} className="flex flex-col gap-2">
              <p className="text-small text-bb-muted">{t(`entry.group.${g.key}`)}</p>
              <div className="grid grid-cols-2 gap-2">
                {g.types.map((ty) => {
                  const Icon = TXN_ICON[ty];
                  return (
                    <button key={ty} type="button" aria-pressed={type === ty} onClick={() => pick(ty)}
                            className={`flex min-h-14 items-center gap-2 rounded-bb border p-2 text-left text-small font-semibold ${
                              type === ty ? "border-bb-primary bg-bb-primary-soft text-bb-primary" : "border-bb-border bg-bb-surface"
                            }`}>
                      <Icon aria-hidden className="size-5 shrink-0" />
                      {t(`txn.${ty}`)}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <p className="flex gap-2 rounded-bb bg-bb-primary-soft p-3 text-small">
            <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-bb-primary" />
            <span><strong>{t(`txn.${type}`)}:</strong> {t(`txn.help.${type}`)}</span>
          </p>
        </fieldset>

        {linkCostItem ? (
          <StatusBanner tone="info" title={t("entry.paying_for", { item: params.get("item_name") ?? "" })} />
        ) : null}

        <AmountInput label={t("entry.amount")} value={amount} onChange={setAmount}
                     hint={t("entry.amount_hint")} errorKey={fields.amount} />
        <Field label={t("entry.date")} type="date" value={date} max={addDays(today, 1)}
               onChange={(e) => setDate(e.target.value)} errorKey={fields.value_date} />

        {showCategory ? (
          <SelectField label={t("entry.category")} value={category} onChange={setCategory}
                       errorKey={fields.category}
                       options={[
                         ...(isFarm ? [{ value: "", label: "—" }] : []),
                         ...categories.map((c) => ({ value: c, label: t(`category.${c}`) })),
                       ]} />
        ) : null}

        {showSupplier ? (
          <div className="flex flex-col gap-1">
            <SelectField label={t("entry.supplier")} value={supplierId} onChange={setSupplierId}
                         errorKey={fields.supplier_id} hint={t("entry.supplier_hint")}
                         options={[{ value: "", label: "—" },
                                   ...suppliers.map((s) => ({ value: s.id, label: s.display_name }))]} />
            <Link to={`/p/${p.id}/suppliers`} className="text-small font-semibold text-bb-primary underline">
              {t("supplier.add")}
            </Link>
          </div>
        ) : null}

        {showDebt ? (
          <div className="flex flex-col gap-1">
            <SelectField label={t("entry.loan")} value={debtId} onChange={setDebtId} errorKey={fields.debt_facility_id}
                         options={[{ value: "", label: "—" },
                                   ...debts.map((d) => ({ value: d.id, label: `${t(`lender_type.${d.lender_type}`)} — ${d.lender_label}` }))]} />
            <Link to={`/p/${p.id}/debts`} className="text-small font-semibold text-bb-primary underline">
              {t("debt.add")}
            </Link>
          </div>
        ) : null}

        {isFarm ? (
          <SelectField label={t("entry.season")} value={seasonId} onChange={setSeasonId}
                       errorKey={fields.season_id ?? fields.season_cost_item_id}
                       options={[{ value: "", label: "—" },
                                 ...seasons.map((s) => ({ value: s.id, label: seasonTitle(s, t) }))]} />
        ) : null}

        <Field label={t("entry.note")} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)}
               hint={t("entry.note_hint")} errorKey={fields.note} />

        {duplicate ? (
          <StatusBanner tone="warning" title={t("entry.duplicate")}>
            {t("entry.duplicate_detail", {
              amount: formatTaka(duplicate.amount, lang), date: formatDate(duplicate.value_date, lang),
            })}
            <div className="mt-2">
              <Button type="button" variant="secondary" busy={busy} onClick={() => void save(true)}>
                {t("entry.duplicate_confirm")}
              </Button>
            </div>
          </StatusBanner>
        ) : null}

        <Button type="submit" full busy={busy}>
          {t("common.save")}
        </Button>
      </form>
    </PageShell>
  );
}

export function seasonTitle(s: Season, t: TFunction): string {
  return [s.crop_name, t(`season.name.${s.season_name}`), s.season_label].filter(Boolean).join(" · ");
}
