import { CheckCircle2, ClipboardCheck, Copy, Landmark, PlusCircle, Sparkles, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type {
  Assessment, DebtList, FinancingRequest, Page, PriceSource, PurposeCategory, Season, SeasonDetail,
} from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Chips } from "../../components/Chips";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate, todayDhaka } from "../../lib/dates";
import { PRICE_SOURCES, PURPOSE_CATEGORIES, editable, orNull } from "../../lib/financing";
import { formatAmount, formatNumber, formatTaka } from "../../lib/format";
import { useActiveProfile, useReloadProfile } from "../../state/ActiveProfile";
import { seasonTitle } from "./AddEntry";

type StepProps = { req: FinancingRequest; setReq: (r: FinancingRequest) => void; next: () => void };

/** PATCH with a short debounce so the live preview follows typing (wizard
 *  autosave, SCR-O11). Field errors come back as i18n keys. */
function useAutosave(pid: string, rid: string, body: Record<string, unknown>, setReq: (r: FinancingRequest) => void) {
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const json = JSON.stringify(body);
  const first = useRef(true);

  const save = useCallback(async (): Promise<boolean> => {
    try {
      setReq(await api<FinancingRequest>(`/profiles/${pid}/financing-requests/${rid}`, { method: "PATCH", body: JSON.parse(json) }));
      setFields({});
      setError(null);
      return true;
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
      return false;
    }
  }, [pid, rid, json, setReq]);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const timer = setTimeout(() => void save(), 600);
    return () => clearTimeout(timer);
  }, [save]);

  return { fields, error, save };
}

function GapBox({ req, lang }: { req: FinancingRequest; lang: Lang }) {
  const { t } = useTranslation();
  const pv = req.preview;
  const rows: [string, string][] = [
    ["fin.items_total", pv.items_total],
    ["fin.gap", pv.funding_gap],
    ["fin.you_asked", req.requested_amount],
  ];
  return (
    <Card className="flex flex-col gap-2 border-bb-primary">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3">
          <span className={k === "fin.gap" ? "font-semibold" : ""}>{t(k)}</span>
          <span className={`tabular ${k === "fin.gap" ? "font-semibold text-bb-primary" : ""}`}>{formatTaka(v, lang)}</span>
        </div>
      ))}
      <p className="text-caption text-bb-muted">{t("fin.gap_formula")}</p>
      {!pv.gap_inputs_complete ? <p className="text-caption text-bb-warning">{t("fin.gap_incomplete")}</p> : null}
    </Card>
  );
}

// ------------------------------------------------------------------ step 1
function ProfileMiniForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const reload = useReloadProfile();
  const [district, setDistrict] = useState(p.district ?? "");
  const [upazila, setUpazila] = useState(p.upazila ?? "");
  const [category, setCategory] = useState(p.business_category ?? "");
  const [household, setHousehold] = useState(editable(p.household_withdrawal_monthly));
  const [fields, setFields] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      await api(`/profiles/${p.id}`, {
        method: "PATCH",
        body: { district: orNull(district), upazila: orNull(upazila), business_category: orNull(category),
                household_withdrawal_monthly: household === "" ? null : household },
      });
      await reload();
      onDone();
    } catch (err) {
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="flex flex-col gap-3">
      <p className="font-semibold">{t("fin.profile_needed")}</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("profile.district")} value={district} onChange={(e) => setDistrict(e.target.value)} errorKey={fields.district} />
        <Field label={t("profile.upazila")} value={upazila} onChange={(e) => setUpazila(e.target.value)} errorKey={fields.upazila} />
      </div>
      <Field label={t("profile.category")} value={category} onChange={(e) => setCategory(e.target.value)}
             hint={t(p.activity_type === "crop_farm" ? "fin.category_hint.farm" : "fin.category_hint")}
             errorKey={fields.business_category} />
      <AmountInput label={t("fin.household")} value={household} onChange={setHousehold}
                   hint={t("fin.household_hint")} errorKey={fields.household_withdrawal_monthly} />
      <Button variant="secondary" busy={busy} onClick={() => void save()}>{t("common.save")}</Button>
    </Card>
  );
}

function StepPurpose({ req, onCreated, setReq, next }: Partial<StepProps> & { onCreated: (r: FinancingRequest) => void; next: () => void }) {
  const { t, i18n } = useTranslation();
  const p = useActiveProfile();
  const isFarm = p.activity_type === "crop_farm";
  const [amount, setAmount] = useState(editable(req?.requested_amount));
  const [purpose, setPurpose] = useState(req?.purpose_text ?? "");
  const [category, setCategory] = useState<PurposeCategory>(req?.purpose_category ?? (isFarm ? "farm_inputs" : "inventory"));
  const [start, setStart] = useState(req?.desired_start_date ?? "");
  const [seasonId, setSeasonId] = useState(req?.season_id ?? "");
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [editProfile, setEditProfile] = useState(false);
  const profileOk = p.household_declared && !!p.district && !!p.upazila;

  useEffect(() => {
    if (isFarm) api<Page<Season>>(`/profiles/${p.id}/seasons`).then((r) => setSeasons(r.items)).catch(() => setSeasons([]));
  }, [p.id, isFarm]);

  const season = seasons.find((s) => s.id === seasonId);
  const seasonGaps = season && (!season.expected_output_low || !season.expected_output_expected || !season.expected_price_low);

  async function submit() {
    if (!amount || Number(amount) <= 0) return setFields({ requested_amount: "entry.err.amount" });
    setBusy(true);
    setFields({});
    const body = { requested_amount: amount, purpose_text: purpose, purpose_category: category,
                   desired_start_date: orNull(start), season_id: isFarm ? orNull(seasonId) : null };
    try {
      if (req && setReq) {
        setReq(await api<FinancingRequest>(`/profiles/${p.id}/financing-requests/${req.id}`, { method: "PATCH", body }));
        next();
      } else {
        onCreated(await api<FinancingRequest>(`/profiles/${p.id}/financing-requests`, { method: "POST", body }));
      }
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ErrorBanner error={error} />
      {!profileOk || editProfile ? (
        <ProfileMiniForm onDone={() => setEditProfile(false)} />
      ) : (
        <p className="flex items-center gap-2 text-small text-bb-muted">
          <CheckCircle2 aria-hidden className="size-4 text-bb-success" />
          {t("fin.household_set", { amount: formatTaka(p.household_withdrawal_monthly ?? "0", i18n.language as Lang) })}
          <button type="button" className="font-semibold text-bb-primary underline" onClick={() => setEditProfile(true)}>
            {t("common.edit")}
          </button>
        </p>
      )}
      <AmountInput label={t("fin.amount")} value={amount} onChange={setAmount} hint={t("fin.amount_hint")}
                   errorKey={fields.requested_amount} />
      <Field label={t("fin.purpose")} value={purpose} maxLength={500} onChange={(e) => setPurpose(e.target.value)}
             hint={t(isFarm ? "fin.purpose_hint.farm" : "fin.purpose_hint")} errorKey={fields.purpose_text} />
      <div className="flex flex-col gap-1">
        <span className="font-semibold">{t("fin.category")}</span>
        <Chips label={t("fin.category")} value={category} onChange={setCategory}
               options={PURPOSE_CATEGORIES.map((c) => ({ value: c, label: t(`fin.cat.${c}`) }))} />
      </div>
      <Field label={t("fin.start_date")} type="date" value={start} min={todayDhaka()}
             onChange={(e) => setStart(e.target.value)} errorKey={fields.desired_start_date} />
      {isFarm ? (
        <div className="flex flex-col gap-1">
          <SelectField label={t("entry.season")} value={seasonId} onChange={setSeasonId} errorKey={fields.season_id}
                       hint={t("fin.season_hint")}
                       options={[{ value: "", label: "—" }, ...seasons.map((s) => ({ value: s.id, label: seasonTitle(s, t) }))]} />
          {seasonGaps ? (
            <StatusBanner tone="warning" title={t("fin.season_estimates_missing")}>
              <Link to={`/p/${p.id}/seasons/${seasonId}/edit`} className="font-semibold text-bb-primary underline">
                {t("common.edit")}
              </Link>
            </StatusBanner>
          ) : null}
        </div>
      ) : null}
      <Button full busy={busy} onClick={() => void submit()}>{t("common.next")}</Button>
    </>
  );
}

// ------------------------------------------------------------------ step 2
type Item = FinancingRequest["items"][number];

/** An AI-suggested item counts only after the owner adds a price and its
 *  source and confirms it (FR-FIN-03; AI never fills prices). */
function AiItemConfirm({ item, url, onDone }: { item: Item; url: string; onDone: () => Promise<void> }) {
  const { t } = useTranslation();
  const [qty, setQty] = useState(item.quantity);
  const [price, setPrice] = useState("");
  const [source, setSource] = useState<PriceSource>("supplier_quote");
  const [fields, setFields] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    setFields({});
    try {
      await api(`${url}/items/${item.id}`, {
        method: "PATCH", body: { quantity: qty, unit_price: price || "0", price_source_type: source, confirmed: true },
      });
      await onDone();
    } catch (err) {
      setFields(err instanceof ApiError && Object.keys(err.fields).length ? err.fields : { unit_price: "err.generic" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-2 flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-2">
        <AmountInput label={`${t("fin.quantity")} (${item.unit})`} value={qty} onChange={setQty} errorKey={fields.quantity} />
        <AmountInput label={t("fin.unit_price")} value={price} onChange={setPrice} errorKey={fields.unit_price} />
      </div>
      <Chips label={t("fin.price_source")} value={source} onChange={setSource}
             options={PRICE_SOURCES.map((s) => ({ value: s, label: t(`price_source.${s}`) }))} />
      <Button variant="secondary" busy={busy} icon={<CheckCircle2 aria-hidden className="size-5" />} onClick={() => void confirm()}>
        {t("fin.ai_confirm_btn")}
      </Button>
    </div>
  );
}

function StepItems({ req, setReq, next }: StepProps) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const url = `/profiles/${p.id}/financing-requests/${req.id}`;
  const [name, setName] = useState("");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("");
  const [price, setPrice] = useState("");
  const [source, setSource] = useState<PriceSource>("supplier_quote");
  const [priceDate, setPriceDate] = useState(todayDhaka());
  const [note, setNote] = useState("");
  const [formKey, setFormKey] = useState(0);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<SeasonDetail | null>(null);

  const reload = useCallback(async () => setReq(await api<FinancingRequest>(url)), [url, setReq]);
  const [parsing, setParsing] = useState(false);
  const [parseNote, setParseNote] = useState<string | null>(null);

  async function parse() {
    setParsing(true);
    setParseNote(null);
    try {
      await api(`${url}/parse-purpose`, { method: "POST", body: {} });
      await reload();
      setParseNote("fin.ai_items_confirm");
    } catch (err) {
      setParseNote(err instanceof ApiError ? err.messageKey : "err.generic"); // manual entry still works
    } finally {
      setParsing(false);
    }
  }

  useEffect(() => {
    if (req.season_id) api<SeasonDetail>(`/profiles/${p.id}/seasons/${req.season_id}`).then(setPlan).catch(() => setPlan(null));
  }, [p.id, req.season_id]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload();
      return true;
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function add() {
    setFields({});
    const ok = await run(() => api(`${url}/items`, {
      method: "POST",
      body: { item_name: name, quantity: qty, unit, unit_price: price, price_source_type: source,
              price_date: orNull(priceDate), price_source_note: orNull(note) },
    }));
    if (ok) {
      setName(""); setQty(""); setUnit(""); setPrice(""); setNote("");
      setFormKey((k) => k + 1);
    }
  }

  const copied = new Set(req.items.map((i) => i.source_season_cost_item_id));
  const copyable = plan?.cost_items.filter((c) => !copied.has(c.id) && Number(c.paid_total) < Number(c.total_cost)) ?? [];

  return (
    <>
      <ErrorBanner error={error} />
      {req.items.length > 0 ? (
        <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
          {req.items.map((i) => (
            <li key={i.id} className="flex items-start gap-2 p-3">
              <div className="flex flex-1 flex-col">
                <span className="font-semibold">{i.item_name}</span>
                <span className="text-small text-bb-muted">
                  {formatNumber(i.quantity, lang)} {i.unit} × {i.unit_price ? formatTaka(i.unit_price, lang) : "—"} · {t(`price_source.${i.price_source_type}`)}
                </span>
                {i.ai_proposed && !i.confirmed ? (
                  <>
                    <span className="text-caption text-bb-warning">{t("fin.ai_confirm")}</span>
                    <AiItemConfirm item={i} url={url} onDone={reload} />
                  </>
                ) : null}
              </div>
              <span className="tabular font-semibold">{formatTaka(i.line_total, lang)}</span>
              <button type="button" aria-label={t("common.delete")} className="flex size-12 items-center justify-center text-bb-danger"
                      onClick={() => void run(() => api(`${url}/items/${i.id}`, { method: "DELETE" }))}>
                <Trash2 aria-hidden className="size-5" />
              </button>
            </li>
          ))}
          <li className="flex justify-between p-3 font-semibold">
            <span>{t("fin.items_total")}</span>
            <span className="tabular">{formatTaka(req.preview.items_total, lang)}</span>
          </li>
        </ul>
      ) : (
        <p className="text-bb-muted">{t("fin.no_items")}</p>
      )}

      {copyable.length > 0 ? (
        <Card className="flex flex-col gap-2">
          <p className="font-semibold">{t("fin.copy_from_plan")}</p>
          {copyable.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-2">
              <span>{c.item_name} · <span className="tabular">{formatTaka(c.total_cost, lang)}</span></span>
              <Button variant="secondary" busy={busy} icon={<Copy aria-hidden className="size-4" />}
                      onClick={() => void run(() => api(`${url}/items`, { method: "POST", body: { copy_from_season_cost_item_id: c.id } }))}>
                {t("fin.copy")}
              </Button>
            </div>
          ))}
        </Card>
      ) : null}

      <Card className="flex flex-col gap-2">
        <p className="font-semibold">{t("fin.ai_parse_title")}</p>
        <p className="text-small text-bb-muted">{t("fin.ai_parse_note")}</p>
        <Button variant="secondary" busy={parsing} icon={<Sparkles aria-hidden className="size-5" />} onClick={() => void parse()}>
          {t("fin.ai_parse")}
        </Button>
        {parseNote ? <StatusBanner tone={parseNote === "fin.ai_items_confirm" ? "info" : "warning"} title={t(parseNote)} /> : null}
      </Card>

      <Card key={formKey} className="flex flex-col gap-3">
        <p className="font-semibold">{t("fin.add_item")}</p>
        <Field label={t("fin.item_name")} value={name} maxLength={120} onChange={(e) => setName(e.target.value)}
               hint={t(p.activity_type === "crop_farm" ? "fin.item_name_hint.farm" : "fin.item_name_hint")}
               errorKey={fields.item_name} />
        <div className="grid grid-cols-2 gap-3">
          <AmountInput label={t("fin.quantity")} value={qty} onChange={setQty} errorKey={fields.quantity} />
          <Field label={t("fin.unit")} value={unit} maxLength={20} onChange={(e) => setUnit(e.target.value)}
                 hint={t("fin.unit_hint")} errorKey={fields.unit} />
        </div>
        <AmountInput label={t("fin.unit_price")} value={price} onChange={setPrice} errorKey={fields.unit_price} />
        <div className="flex flex-col gap-1">
          <span className="font-semibold">{t("fin.price_source")}</span>
          <Chips label={t("fin.price_source")} value={source} onChange={setSource}
                 options={PRICE_SOURCES.map((s) => ({ value: s, label: t(`price_source.${s}`) }))} />
        </div>
        <Field label={t("fin.price_date")} type="date" value={priceDate} max={todayDhaka()}
               onChange={(e) => setPriceDate(e.target.value)} errorKey={fields.price_date} />
        <Field label={t("fin.price_note")} value={note} maxLength={200} onChange={(e) => setNote(e.target.value)}
               hint={t(p.activity_type === "crop_farm" ? "fin.price_note_hint.farm" : "fin.price_note_hint")}
               errorKey={fields.price_source_note} />
        <Button variant="secondary" busy={busy} icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => void add()}>
          {t("fin.add_item")}
        </Button>
      </Card>
      <Button full onClick={next} disabled={req.items.length === 0}>{t("common.next")}</Button>
    </>
  );
}

// ------------------------------------------------------------------ step 3
function StepMoney({ req, setReq, next }: StepProps) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [assoc, setAssoc] = useState(editable(req.associated_expenses));
  const [buffer, setBuffer] = useState(editable(req.liquidity_buffer));
  const [why, setWhy] = useState(req.buffer_justification ?? "");
  const [cash, setCash] = useState(editable(req.cash_safely_available));
  const [committed, setCommitted] = useState(editable(req.committed_financing));
  const [current, setCurrent] = useState(editable(req.current_cash_balance));
  const [explain, setExplain] = useState(req.over_request_explanation ?? "");
  const { fields, error, save } = useAutosave(p.id, req.id, {
    associated_expenses: orNull(assoc), liquidity_buffer: orNull(buffer), buffer_justification: orNull(why),
    cash_safely_available: orNull(cash), committed_financing: orNull(committed), current_cash_balance: orNull(current),
    over_request_explanation: orNull(explain),
  }, setReq);
  const over = req.preview.gap_inputs_complete && Number(req.preview.request_minus_gap) > 0;

  return (
    <>
      <ErrorBanner error={error} />
      <AmountInput label={t("fin.associated")} value={assoc} onChange={setAssoc} hint={t("fin.associated_hint")}
                   errorKey={fields.associated_expenses} />
      <AmountInput label={t("fin.buffer")} value={buffer} onChange={setBuffer} hint={t("fin.buffer_hint")}
                   errorKey={fields.liquidity_buffer} />
      {Number(buffer) > 0 ? (
        <Field label={t("fin.buffer_why")} value={why} maxLength={500} onChange={(e) => setWhy(e.target.value)}
               errorKey={fields.buffer_justification} />
      ) : null}
      <AmountInput label={t("fin.cash_available")} value={cash} onChange={setCash} hint={t("fin.cash_available_hint")}
                   errorKey={fields.cash_safely_available} />
      <AmountInput label={t("fin.committed")} value={committed} onChange={setCommitted} hint={t("fin.committed_hint")}
                   errorKey={fields.committed_financing} />
      <AmountInput label={t("fin.current_cash")} value={current} onChange={setCurrent} hint={t("fin.current_cash_hint")}
                   errorKey={fields.current_cash_balance} />
      <GapBox req={req} lang={lang} />
      {over ? (
        <Field label={t("fin.over_request", { diff: formatAmount(req.preview.request_minus_gap ?? "0", lang) })}
               value={explain} maxLength={500} onChange={(e) => setExplain(e.target.value)}
               hint={t("fin.over_request_hint")} errorKey={fields.over_request_explanation} />
      ) : null}
      <Button full onClick={() => void save().then((ok) => ok && next())}>{t("common.next")}</Button>
    </>
  );
}

// ------------------------------------------------------------------ step 4
function StepLoans({ next }: StepProps) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const { rid } = useParams();
  const [data, setData] = useState<DebtList | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    api<DebtList>(`/profiles/${p.id}/debts`).then(setData).catch(setError);
  }, [p.id]);
  useEffect(load, [load]);

  const active = data?.items.filter((d) => d.status === "active") ?? [];
  const declared = active.length > 0 || data?.no_debt_declared;

  async function none() {
    setBusy(true);
    try {
      await api(`/profiles/${p.id}/debts/declare-none`, { method: "POST" });
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <><ErrorBanner error={error} /><Loading /></>;
  return (
    <>
      <ErrorBanner error={error} />
      <p className="text-small text-bb-muted">{t("fin.loans_help")}</p>
      {active.map((d) => (
        <Card key={d.id} className="flex items-center gap-3">
          <Landmark aria-hidden className="size-5 text-bb-primary" />
          <div className="flex flex-1 flex-col">
            <span className="font-semibold">{t(`lender_type.${d.lender_type}`)} — {d.lender_label}</span>
            <span className="text-small text-bb-muted">
              {formatTaka(d.outstanding_balance, lang)}
              {d.next_due_date ? ` · ${t("debt.next_due")} ${formatDate(d.next_due_date, lang)}` : ""}
            </span>
          </div>
          {d.is_overdue ? <span className="text-caption font-semibold text-bb-danger">{t("debt.overdue")}</span> : null}
        </Card>
      ))}
      {data.no_debt_declared && active.length === 0 ? <StatusBanner tone="success" title={t("debt.none_declared")} /> : null}
      <Link to={`/p/${p.id}/debts?back=${encodeURIComponent(`/p/${p.id}/financing/${rid}/step/4`)}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-bb border border-bb-primary font-semibold text-bb-primary">
        <PlusCircle aria-hidden className="size-5" />{t("debt.add")}
      </Link>
      {active.length === 0 && !data.no_debt_declared ? (
        <Button variant="secondary" full busy={busy} onClick={() => void none()}>{t("debt.none")}</Button>
      ) : null}
      <p className="text-small text-bb-muted">{t("debt.cib")}</p>
      <Button full onClick={next} disabled={!declared}>{t("common.next")}</Button>
    </>
  );
}

// ------------------------------------------------------------------ step 5
type FitOption = {
  label: "safest" | "fastest" | "smallest_installment" | "closest";
  schedule_type: "equal_installments" | "single_payment"; installment_count: number | null;
  installment_frequency: "weekly" | "monthly" | null; first_due_date: string; last_due_date: string;
  installment_amount: string; total_repayment: string; margin: string; shortfall: string;
};
type FitResult = {
  blocked_by: string[]; options: FitOption[]; closest: FitOption | null; tried: number; fit_count: number;
  margin_kind: "surplus_at_due_date" | "lowest_balance_above_reserve";
};

/** Repayment Fit Finder (SUG-56): the server tries many schedules through the same check as the result
 *  screen and shows up to three that fit. The owner picks; it stays their own proposal. */
function FitFinder({ url, save, onUse }: { url: string; save: () => Promise<boolean>; onUse: (o: FitOption) => Promise<void> }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const [res, setRes] = useState<FitResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function find() {
    setBusy(true);
    setError(null);
    try {
      await save(); // the reserve and interest typed below are part of the check
      setRes(await api<FitResult>(`${url}/schedule-options`));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const describe = (o: FitOption) => o.schedule_type === "single_payment"
    ? t("fit.single", { amount: formatTaka(o.total_repayment, lang), date: formatDate(o.first_due_date, lang) })
    : t(`fit.equal.${o.installment_frequency}`, {
        n: formatNumber(String(o.installment_count), lang), amount: formatTaka(o.installment_amount, lang),
        first: formatDate(o.first_due_date, lang), last: formatDate(o.last_due_date, lang) });

  return (
    <Card className="flex flex-col gap-3">
      <p className="font-semibold">{t("fit.title")}</p>
      <p className="text-small text-bb-muted">{t("fit.intro")}</p>
      <Button variant="secondary" busy={busy} icon={<Sparkles aria-hidden className="size-5" />} onClick={() => void find()}>
        {t("fit.find")}
      </Button>
      <ErrorBanner error={error} />
      {res && res.blocked_by.length > 0 ? (
        <StatusBanner tone="warning" title={t("fit.blocked")}>
          <ul className="list-disc pl-5">{res.blocked_by.map((m) => <li key={m}>{t(`missing.${m}`)}</li>)}</ul>
        </StatusBanner>
      ) : null}
      {res && res.blocked_by.length === 0 && res.options.length === 0 ? (
        <StatusBanner tone="warning" title={t("fit.none")}>
          {res.closest ? (
            <p>{t("fit.closest", { plan: describe(res.closest), amount: formatTaka(res.closest.shortfall, lang) })}</p>
          ) : null}
          <p>{t("fit.none_next")}</p>
        </StatusBanner>
      ) : null}
      {res?.options.map((o) => (
        <div key={o.label} className="flex flex-col gap-2 rounded-bb border border-bb-border p-3">
          <p className="font-semibold text-bb-primary">{t(`fit.label.${o.label}`)}</p>
          <p>{describe(o)}</p>
          <p className="text-small text-bb-muted">
            {t(`fit.margin.${res.margin_kind}`, { amount: formatTaka(o.margin, lang) })}
          </p>
          <Button variant="secondary" icon={<CheckCircle2 aria-hidden className="size-5" />} onClick={() => void onUse(o)}>
            {t("fit.use")}
          </Button>
        </div>
      ))}
      {res && res.options.length > 0 ? (
        <p className="text-small text-bb-muted">{t("fit.note", { tried: formatNumber(String(res.tried), lang) })}</p>
      ) : null}
    </Card>
  );
}

function StepTerms({ req, setReq }: StepProps) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [type, setType] = useState(req.schedule_type ?? "equal_installments");
  const [count, setCount] = useState(req.installment_count ? String(req.installment_count) : "");
  const [freq, setFreq] = useState(req.installment_frequency ?? (p.activity_type === "crop_farm" ? "monthly" : "weekly"));
  const [first, setFirst] = useState(req.first_due_date ?? "");
  const [interest, setInterest] = useState(editable(req.interest_fees_total));
  const [unknown, setUnknown] = useState(req.interest_fees_unknown);
  const [reserve, setReserve] = useState(editable(req.minimum_cash_reserve));
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<unknown>(null);
  const equal = type === "equal_installments";
  const n = Number(count);
  const { fields, error, save } = useAutosave(p.id, req.id, {
    schedule_type: type, installment_count: equal ? (Number.isInteger(n) && n >= 1 && n <= 60 ? n : null) : 1,
    installment_frequency: equal ? freq : null, first_due_date: orNull(first),
    ...(unknown ? { interest_fees_unknown: true } : { interest_fees_unknown: false, interest_fees_total: orNull(interest) }),
    minimum_cash_reserve: orNull(reserve),
  }, setReq);

  async function check() {
    setBusy(true);
    setRunError(null);
    try {
      if (!(await save())) return;
      const a = await api<Assessment>(`/profiles/${p.id}/financing-requests/${req.id}/assessments`, { method: "POST" });
      void navigate(`/p/${p.id}/assessment/${a.id}`);
    } catch (err) {
      setRunError(err);
    } finally {
      setBusy(false);
    }
  }

  async function applyOption(o: FitOption) {
    setRunError(null);
    try {
      setReq(await api<FinancingRequest>(`/profiles/${p.id}/financing-requests/${req.id}`, {
        method: "PATCH",
        body: { schedule_type: o.schedule_type, installment_count: o.installment_count ?? 1,
                installment_frequency: o.installment_frequency, first_due_date: o.first_due_date },
      }));
      setType(o.schedule_type);
      setCount(o.installment_count ? String(o.installment_count) : "");
      if (o.installment_frequency) setFreq(o.installment_frequency);
      setFirst(o.first_due_date);
    } catch (err) {
      setRunError(err);
    }
  }

  const rows = req.preview.installments;
  return (
    <>
      <StatusBanner tone="info" title={t("fin.proposal_banner")} />
      <ErrorBanner error={error ?? runError} />
      <FitFinder url={`/profiles/${p.id}/financing-requests/${req.id}`} save={save} onUse={applyOption} />
      <div className="flex flex-col gap-1">
        <span className="font-semibold">{t("fin.schedule")}</span>
        <Chips label={t("fin.schedule")} value={type} onChange={setType}
               options={[{ value: "equal_installments", label: t("fin.equal") }, { value: "single_payment", label: t("fin.single") }]} />
      </div>
      {equal ? (
        <>
          <Field label={t("fin.count")} inputMode="numeric" value={count} errorKey={fields.installment_count}
                 onChange={(e) => setCount(e.target.value.replace(/[০-৯]/g, (d) => String("০১২৩৪৫৬৭৮৯".indexOf(d))).replace(/\D/g, ""))} />
          <div className="flex flex-col gap-1">
            <span className="font-semibold">{t("debt.frequency")}</span>
            <Chips label={t("debt.frequency")} value={freq} onChange={setFreq}
                   options={[{ value: "weekly", label: t("debt.freq.weekly") }, { value: "monthly", label: t("debt.freq.monthly") }]} />
          </div>
        </>
      ) : null}
      <Field label={equal ? t("fin.first_due") : t("debt.due_date")} type="date" value={first} min={todayDhaka()}
             onChange={(e) => setFirst(e.target.value)} errorKey={fields.first_due_date} />
      {!unknown ? (
        <AmountInput label={t("fin.interest")} value={interest} onChange={setInterest} hint={t("fin.interest_hint")}
                     errorKey={fields.interest_fees_total} />
      ) : null}
      <label className="flex min-h-12 items-center gap-3">
        <input type="checkbox" checked={unknown} onChange={(e) => setUnknown(e.target.checked)} className="size-5" />
        {t("fin.interest_unknown")}
      </label>
      <AmountInput label={t("fin.reserve")} value={reserve} onChange={setReserve} hint={t("fin.reserve_hint")}
                   errorKey={fields.minimum_cash_reserve} />
      {rows.length > 0 ? (
        <Card className="p-0">
          <p className="px-4 pt-3 font-semibold">{t("fin.installments")}</p>
          <ul className="divide-y divide-bb-border">
            {rows.slice(0, 12).map((r, i) => (
              <li key={r.due_date + i} className="flex justify-between px-4 py-2 text-small">
                <span>{formatNumber(String(i + 1), lang)}. {formatDate(r.due_date, lang)}</span>
                <span className="tabular">{formatTaka(r.amount, lang)}</span>
              </li>
            ))}
            {rows.length > 12 ? <li className="px-4 py-2 text-small text-bb-muted">… {formatNumber(String(rows.length), lang)}</li> : null}
            <li className="flex justify-between px-4 py-2 font-semibold">
              <span>{t("fin.repayment_total")}</span>
              <span className="tabular">{formatTaka(req.preview.repayment_total ?? "0", lang)}</span>
            </li>
          </ul>
        </Card>
      ) : null}
      <Button full busy={busy} icon={<ClipboardCheck aria-hidden className="size-5" />} onClick={() => void check()}>
        {t("fin.check")}
      </Button>
    </>
  );
}

// ------------------------------------------------------------------ shell
const STEP_TITLES = ["fin.step1", "fin.step2", "fin.step3", "fin.step4", "fin.step5"];

function Progress({ n }: { n: number }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  return (
    <div className="flex flex-col gap-1">
      <p className="text-small text-bb-muted">
        {t("fin.step_of", { n: formatNumber(String(n), lang), total: formatNumber("5", lang) })}
      </p>
      <div className="flex gap-1" aria-hidden>
        {[1, 2, 3, 4, 5].map((i) => <div key={i} className={`h-2 flex-1 rounded-full ${i <= n ? "bg-bb-primary" : "bg-bb-border"}`} />)}
      </div>
    </div>
  );
}

/** SCR-O11 Financing wizard. /financing/new creates the request at step 1;
 *  /financing/:rid/step/:n edits it, each step saved to the server. */
export function FinancingWizard() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const navigate = useNavigate();
  const { rid, n } = useParams();
  const step = rid ? Math.min(5, Math.max(1, Number(n) || 1)) : 1;
  const [req, setReq] = useState<FinancingRequest | null>(null);
  const [error, setError] = useState<unknown>(null);
  const base = `/p/${p.id}/financing`;

  useEffect(() => {
    if (!rid) return;
    api<FinancingRequest>(`/profiles/${p.id}/financing-requests/${rid}`).then(setReq).catch(setError);
  }, [p.id, rid]);

  const go = (k: number) => void navigate(`${base}/${rid}/step/${k}`);
  const back = step > 1 && rid ? `${base}/${rid}/step/${step - 1}` : base;
  let body: ReactNode;
  if (!rid) {
    body = <StepPurpose onCreated={(r) => void navigate(`${base}/${r.id}/step/2`)} next={() => undefined} />;
  } else if (!req) {
    body = <><ErrorBanner error={error} />{error ? null : <Loading />}</>;
  } else {
    const props = { req, setReq, next: () => go(step + 1) };
    body = [
      <StepPurpose key="1" {...props} onCreated={() => undefined} />,
      <StepItems key="2" {...props} />,
      <StepMoney key="3" {...props} />,
      <StepLoans key="4" {...props} />,
      <StepTerms key="5" {...props} />,
    ][step - 1];
  }
  return (
    <PageShell title={t(STEP_TITLES[step - 1])} back={back}>
      <Progress n={step} />
      {body}
    </PageShell>
  );
}
