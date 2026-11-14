import { Lock, Pencil, PlusCircle, Truck } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { Page, Supplier } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { toBanglaDigits } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

type Form = { display_name: string; goods_supplied: string; district: string; upazila: string; share: string };
const EMPTY: Form = { display_name: "", goods_supplied: "", district: "", upazila: "", share: "" };

function SupplierForm({ initial, onSaved, onCancel, supplierId }: {
  initial: Form; supplierId?: string; onSaved: () => void; onCancel: () => void;
}) {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const [f, setF] = useState(initial);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Form) => (v: string) => setF((cur) => ({ ...cur, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    try {
      await api(supplierId ? `/profiles/${p.id}/suppliers/${supplierId}` : `/profiles/${p.id}/suppliers`, {
        method: supplierId ? "PATCH" : "POST",
        body: {
          display_name: f.display_name, goods_supplied: f.goods_supplied || null, district: f.district || null,
          upazila: f.upazila || null, declared_purchase_share_pct: f.share || null,
        },
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
        <Field label={t("supplier.name")} value={f.display_name} maxLength={80} hint={t("supplier.name_hint")}
               onChange={(e) => set("display_name")(e.target.value)} errorKey={fields.display_name} />
        <Field label={t("supplier.goods")} value={f.goods_supplied} maxLength={120} hint={t("supplier.goods_hint")}
               onChange={(e) => set("goods_supplied")(e.target.value)} errorKey={fields.goods_supplied} />
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("profile.district")} value={f.district} maxLength={120}
                 onChange={(e) => set("district")(e.target.value)} errorKey={fields.district} />
          <Field label={t("profile.upazila")} value={f.upazila} maxLength={120}
                 onChange={(e) => set("upazila")(e.target.value)} errorKey={fields.upazila} />
        </div>
        <AmountInput label={t("supplier.share")} value={f.share} onChange={set("share")}
                     hint={t("supplier.share_hint")} errorKey={fields.declared_purchase_share_pct} />
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>
          <Button type="submit" busy={busy}>{t("common.save")}</Button>
        </div>
      </form>
    </Card>
  );
}

/** SCR-O08 Suppliers (FR-SUP-01/02). The dependency bar arrives with
 *  supplier-concentration in P4; names are never shown to lenders. */
export function Suppliers() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [items, setItems] = useState<Supplier[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);

  const load = useCallback(() => {
    api<Page<Supplier>>(`/profiles/${p.id}/suppliers`).then((r) => setItems(r.items)).catch(setError);
  }, [p.id]);
  useEffect(load, [load]);

  async function toggle(s: Supplier) {
    try {
      await api(`/profiles/${p.id}/suppliers/${s.id}`, { method: "PATCH", body: { is_active: !s.is_active } });
      load();
    } catch (err) {
      setError(err);
    }
  }

  const done = () => { setEditing(null); load(); };
  const pct = (v: string) => (lang === "bn" ? toBanglaDigits(v.replace(/\.00$/, "")) : v.replace(/\.00$/, ""));

  return (
    <PageShell title={t("supplier.title")} back={`/p/${p.id}/more`}>
      <ErrorBanner error={error} />
      {editing === "new" ? (
        <SupplierForm initial={EMPTY} onSaved={done} onCancel={() => setEditing(null)} />
      ) : (
        <Button full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => setEditing("new")}>
          {t("supplier.add")}
        </Button>
      )}
      {!items && !error ? <Loading /> : null}
      {items && items.length === 0 && editing !== "new" ? (
        <EmptyState icon={<Truck className="size-10" />} message={t("supplier.add_prompt")} />
      ) : null}
      {items?.map((s) => editing === s.id ? (
        <SupplierForm key={s.id} supplierId={s.id} onSaved={done} onCancel={() => setEditing(null)}
                      initial={{ display_name: s.display_name, goods_supplied: s.goods_supplied ?? "",
                                 district: s.district ?? "", upazila: s.upazila ?? "",
                                 share: s.declared_purchase_share_pct?.replace(/\.00$/, "") ?? "" }} />
      ) : (
        <Card key={s.id} className={`flex flex-col gap-1 ${s.is_active ? "" : "opacity-70"}`}>
          <div className="flex items-start justify-between gap-2">
            <p className="flex items-center gap-2 font-semibold">
              <Truck aria-hidden className="size-5 text-bb-primary" />
              {s.display_name}
            </p>
            <button type="button" onClick={() => setEditing(s.id)} aria-label={t("common.edit")}
                    className="flex min-h-12 min-w-12 items-center justify-center text-bb-primary">
              <Pencil aria-hidden className="size-5" />
            </button>
          </div>
          {s.goods_supplied ? <p className="text-small">{s.goods_supplied}</p> : null}
          <p className="text-small text-bb-muted">
            {[s.upazila, s.district].filter(Boolean).join(", ")}
            {s.declared_purchase_share_pct ? ` · ${t("supplier.share_short", { pct: pct(s.declared_purchase_share_pct) })}` : ""}
          </p>
          {!s.is_active ? <p className="text-small font-semibold text-bb-muted">{t("supplier.inactive")}</p> : null}
          <button type="button" onClick={() => void toggle(s)} className="min-h-12 self-start text-small font-semibold text-bb-primary underline">
            {s.is_active ? t("supplier.deactivate") : t("supplier.activate")}
          </button>
        </Card>
      ))}
      <p className="flex gap-2 text-small text-bb-muted">
        <Lock aria-hidden className="mt-0.5 size-4 shrink-0" />
        {t("supplier.private_note")}
      </p>
    </PageShell>
  );
}
