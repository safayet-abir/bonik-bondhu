import type { TFunction } from "i18next";
import { Camera, FileText, Paperclip, PlusCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Page, Transaction } from "../../api/types";
import { Button } from "../../components/Button";
import { Chips } from "../../components/Chips";
import { EmptyState } from "../../components/EmptyState";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import { cashDirection, LIST_FILTERS, TXN_ICON } from "../../lib/txn";
import { useActiveProfile } from "../../state/ActiveProfile";

const PAGE = 50;
type Filter = keyof typeof LIST_FILTERS;

export function entryLabel(tx: Transaction, t: TFunction): string {
  return tx.category ? t(`category.${tx.category}`, { defaultValue: tx.category }) : t(`txn.${tx.txn_type}`);
}

/** One ledger row: icon, label, date, amount (green = cash in), 📎 evidence, voided struck through. */
export function EntryRow({ tx, to }: { tx: Transaction; to: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const Icon = TXN_ICON[tx.txn_type];
  const dir = cashDirection(tx.txn_type);
  const voided = tx.status === "voided";
  return (
    <li>
      <Link to={to} className="flex min-h-14 items-center gap-3 p-3">
        <Icon aria-hidden className={`size-5 shrink-0 ${dir === "in" ? "text-bb-success" : "text-bb-muted"}`} />
        <span className="flex-1">
          <span className={`block ${voided ? "line-through text-bb-muted" : ""}`}>{entryLabel(tx, t)}</span>
          <span className="flex items-center gap-1 text-small text-bb-muted">
            {formatDate(tx.value_date, lang)}
            {tx.category ? ` · ${t(`txn.${tx.txn_type}`)}` : ""}
            {tx.supplier ? ` · ${tx.supplier.display_name}` : ""}
            {tx.evidence_state === "document_attached" ? <Paperclip aria-label={t("entry.has_document")} className="size-4" /> : null}
          </span>
          {voided ? <span className="text-small font-semibold text-bb-danger">{t("entry.voided")}</span> : null}
        </span>
        <span className={`tabular font-semibold whitespace-nowrap ${voided ? "line-through text-bb-muted" : dir === "in" ? "text-bb-success" : ""}`}>
          {formatTaka(tx.amount, lang)}
        </span>
      </Link>
    </li>
  );
}

/** SCR-O06 Entries list with filter chips All · In · Out · Loans · Voided. */
export function Entries() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const navigate = useNavigate();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const [filter, setFilter] = useState<Filter>("all");
  const [items, setItems] = useState<Transaction[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback((f: Filter, offset: number) => {
    const q = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
    const spec = LIST_FILTERS[f];
    spec.types?.forEach((ty) => q.append("txn_type", ty));
    if (spec.status) q.set("status", spec.status);
    return api<Page<Transaction>>(`/profiles/${p.id}/transactions?${q}`);
  }, [p.id]);

  useEffect(() => {
    setItems(null);
    load(filter, 0).then((r) => { setItems(r.items); setTotal(r.total); }).catch(setError);
  }, [filter, load]);

  function more() {
    if (!items) return;
    load(filter, items.length).then((r) => setItems([...items, ...r.items])).catch(setError);
  }

  return (
    <PageShell title={t("entries.title")}>
      {notice ? <StatusBanner tone="success" title={t(notice)} /> : null}
      <Button full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => navigate(`/p/${p.id}/entries/new?back=/p/${p.id}/entries`)}>
        {t("entry.new")}
      </Button>
      <Button full variant="secondary" icon={<Camera aria-hidden className="size-5" />} onClick={() => navigate(`/p/${p.id}/photo`)}>
        {t("entries.photo")}
      </Button>
      <Chips label={t("entries.filter")} value={filter} onChange={setFilter}
             options={(Object.keys(LIST_FILTERS) as Filter[]).map((f) => ({ value: f, label: t(`entries.filter.${f}`) }))} />
      <ErrorBanner error={error} />
      {!items && !error ? <Loading /> : null}
      {items && items.length === 0 ? (
        <EmptyState icon={<FileText className="size-10" />} message={t("entries.empty")} />
      ) : null}
      {items && items.length > 0 ? (
        <ul className="divide-y divide-bb-border rounded-xl bb-hard-sm bg-bb-surface">
          {items.map((tx) => <EntryRow key={tx.id} tx={tx} to={`/p/${p.id}/entries/${tx.id}`} />)}
        </ul>
      ) : null}
      {items && items.length < total ? (
        <Button variant="secondary" full onClick={more}>{t("common.load_more")}</Button>
      ) : null}
    </PageShell>
  );
}
