import {
  AlertTriangle, Ban, Check, Copy, Eye, KeyRound, MessageSquare, RefreshCw, Send, ShieldCheck, X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, ApiError } from "../../api/client";
import type { ConsentActivity, ConsentList, ConsentRow, FinancingRequest, Page, SectionKey } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Chips } from "../../components/Chips";
import { DemoBadge } from "../../components/DemoBadge";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatNumber, formatTaka } from "../../lib/format";
import { formatShareCode, shortHash, sortSections } from "../../lib/sharing";
import { useActiveProfile, useReloadProfile } from "../../state/ActiveProfile";

const day = (iso: string | null, lang: Lang) => (iso ? formatDate(iso.slice(0, 10), lang) : "—");

function ShareCode() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const reload = useReloadProfile();
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const code = formatShareCode(p.share_code);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }
  async function regenerate() {
    setBusy(true);
    try {
      await api(`/profiles/${p.id}/share-code/regenerate`, { method: "POST" });
      await reload();
      setConfirm(false);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card className="flex flex-col gap-3">
      <ErrorBanner error={error} />
      <p className="flex items-center gap-2 font-semibold"><KeyRound aria-hidden className="size-5 text-bb-primary" />{t("share.code_title")}</p>
      <p className="tabular text-center text-2xl font-semibold tracking-widest" aria-label={t("share.code_title")}>{code}</p>
      <p className="text-small">{t("share.code_help")}</p>
      <p className="text-small text-bb-muted">{t("share.code_locator")}</p>
      <div className="grid grid-cols-2 gap-3">
        <Button variant="secondary" icon={<Copy aria-hidden className="size-4" />} onClick={() => void copy()}>
          {copied ? t("share.copied") : t("share.copy")}
        </Button>
        <Button variant="secondary" icon={<RefreshCw aria-hidden className="size-4" />} onClick={() => setConfirm(true)}>
          {t("share.new_code")}
        </Button>
      </div>
      {confirm ? (
        <div className="flex flex-col gap-2 rounded-lg bg-bb-bg p-3 text-small">
          <p>{t("share.new_code_confirm")}</p>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" onClick={() => setConfirm(false)}>{t("common.cancel")}</Button>
            <Button busy={busy} onClick={() => void regenerate()}>{t("share.new_code")}</Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}

function ApproveSheet({ c, list, requests, onDone, onCancel }: {
  c: ConsentRow; list: ConsentList; requests: FinancingRequest[]; onDone: () => void; onCancel: () => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const required = list.required_sections;
  const [sections, setSections] = useState<SectionKey[]>(
    sortSections([...new Set([...required, ...c.requested_sections.filter((s) => list.allowed_sections.includes(s))])]));
  const [rid, setRid] = useState(requests[0]?.id ?? "");
  const [days, setDays] = useState("14");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const toggle = (s: SectionKey) =>
    setSections((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : sortSections([...cur, s])));

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      await api(`/profiles/${p.id}/consents/${c.id}/approve`, {
        method: "POST", body: { approved_sections: sections, financing_request_id: rid, valid_days: Number(days) },
      });
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  const stale = error instanceof ApiError && error.code === "ASSESSMENT_STALE";
  const chosen = requests.find((r) => r.id === rid);
  return (
    <div className="flex flex-col gap-3 border-t border-bb-border pt-3">
      {stale ? (
        <StatusBanner tone="warning" title={t("consent.err.assessment_stale")}>
          {chosen ? <Link className="font-semibold underline" to={`/p/${p.id}/financing/${chosen.id}/step/5`}>{t("share.run_check")}</Link> : null}
        </StatusBanner>
      ) : <ErrorBanner error={error} />}
      {requests.length === 0 ? (
        <p className="text-small">{t("share.no_request")} <Link className="font-semibold underline" to={`/p/${p.id}/financing/new`}>{t("fin.new")}</Link></p>
      ) : (
        <SelectField label={t("share.which_request")} value={rid} onChange={setRid}
                     options={requests.map((r) => ({ value: r.id, label: `${formatTaka(r.requested_amount, lang)} ·${r.purpose_text.slice(0, 40)}` }))} />
      )}
      <fieldset className="flex flex-col gap-1">
        <legend className="mb-1 font-semibold">{t("share.what_to_show")}</legend>
        {list.allowed_sections.map((s) => {
          const locked = required.includes(s);
          return (
            <label key={s} className="flex min-h-12 items-center gap-3">
              <input type="checkbox" className="size-5 accent-bb-primary" checked={sections.includes(s)}
                     disabled={locked} onChange={() => toggle(s)} />
              <span>
                {t(`section.${s}`)}
                {locked ? <span className="text-small text-bb-muted"> · {t("share.required")}</span> : null}
                {!c.requested_sections.includes(s) && !locked ? <span className="text-small text-bb-muted"> · {t("share.not_asked")}</span> : null}
              </span>
            </label>
          );
        })}
      </fieldset>
      <div className="flex flex-col gap-1">
        <p className="font-semibold">{t("share.how_long")}</p>
        <Chips label={t("share.how_long")} value={days} onChange={setDays}
               options={list.valid_days.map((d) => ({ value: String(d), label: t("share.days", { n: d }) }))} />
      </div>
      <p className="flex gap-2 text-small font-semibold text-bb-warning">
        <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0" />{t("share.warning")}
      </p>
      <p className="text-small text-bb-muted">{t("share.snapshot_note")}</p>
      <div className="grid grid-cols-2 gap-3">
        <Button variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>
        <Button busy={busy} disabled={!rid} icon={<Check aria-hidden className="size-4" />} onClick={() => void approve()}>
          {t("share.approve")}
        </Button>
      </div>
    </div>
  );
}

function Activity({ c }: { c: ConsentRow }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [a, setA] = useState<ConsentActivity | null>(null);
  useEffect(() => {
    api<ConsentActivity>(`/profiles/${p.id}/consents/${c.id}/activity`).then(setA).catch(() => setA(null));
  }, [p.id, c.id, c.read_count, c.open_info_requests, c.decision?.at]);
  if (!a) return null;
  return (
    <div className="flex flex-col gap-2 text-small">
      {a.decision ? (
        <StatusBanner tone="info" title={t("share.decision", { org: a.decision.organization, decision: t(`decision.${a.decision.decision}`) })}>
          <p>{a.decision.reason}</p>
          <p className="mt-1">{t("lender.decision_banner")}</p>
        </StatusBanner>
      ) : null}
      {a.info_requests.map((m) => (
        <p key={m.at} className="flex gap-2 rounded-lg bg-bb-primary-soft p-2">
          <MessageSquare aria-hidden className="mt-0.5 size-4 shrink-0 text-bb-primary" />
          <span><span className="font-semibold">{t("share.lender_message")}</span> ({day(m.at, lang)}): {m.body}</span>
        </p>
      ))}
      {a.reads.length > 0 ? (
        <p className="flex gap-2 text-bb-muted">
          <Eye aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t("share.viewed_list", { list: day(a.reads[0].at, lang), org: a.reads[0].organization })}
        </p>
      ) : <p className="text-bb-muted">{t("share.not_viewed")}</p>}
    </div>
  );
}

/** SCR-O14 Sharing & lender requests (FR-CON-02..09). The owner decides what a
 *  lender sees and for how long; nothing is shared without approval. */
export function Sharing() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [list, setList] = useState<ConsentList | null>(null);
  const [requests, setRequests] = useState<FinancingRequest[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    api<ConsentList>(`/profiles/${p.id}/consents`).then(setList).catch(setError);
    api<Page<FinancingRequest>>(`/profiles/${p.id}/financing-requests`).then((r) => setRequests(r.items)).catch(setError);
  }, [p.id]);
  useEffect(load, [load]);

  async function act(c: ConsentRow, action: "decline" | "revoke" | "reshare") {
    setBusy(`${c.id}:${action}`);
    setError(null);
    try {
      await api(`/profiles/${p.id}/consents/${c.id}/${action}`, { method: "POST" });
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  const items = list?.items ?? [];
  const pending = items.filter((c) => c.status === "requested");
  const active = items.filter((c) => c.status === "approved" && !c.is_expired);
  const closed = items.filter((c) => c.status === "declined" || c.status === "revoked" || c.is_expired);

  const head = (c: ConsentRow) => (
    <div className="flex flex-col gap-1">
      <p className="flex flex-wrap items-center gap-2 font-semibold">
        {c.lender_organization.name} {c.lender_organization.is_demo ? <DemoBadge /> : null}
      </p>
      {c.requested_by ? <p className="text-small text-bb-muted">{t("share.officer", { name: c.requested_by })}</p> : null}
    </div>
  );

  return (
    <PageShell title={t("share.title")} back={`/p/${p.id}/more`}>
      <ShareCode />
      <ErrorBanner error={error} />
      {!list && !error ? <Loading /> : null}

      <h2 className="font-semibold">{t("share.new_requests")} {pending.length ? `(${formatNumber(String(pending.length), lang)})` : ""}</h2>
      {list && pending.length === 0 ? <p className="text-small text-bb-muted">{t("share.no_requests")}</p> : null}
      {pending.map((c) => (
        <Card key={c.id} className="flex flex-col gap-2">
          {head(c)}
          <p className="text-small">{t("share.wants")}: {c.requested_sections.map((s) => t(`section.${s}`)).join(", ")}</p>
          {c.request_message ? <p className="rounded-lg bg-bb-bg p-2 text-small">“{c.request_message}”</p> : null}
          <p className="text-small text-bb-muted">{day(c.created_at, lang)}</p>
          {open === c.id && list ? (
            <ApproveSheet c={c} list={list} requests={requests} onCancel={() => setOpen(null)}
                          onDone={() => { setOpen(null); load(); }} />
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" busy={busy === `${c.id}:decline`} icon={<X aria-hidden className="size-4" />}
                      onClick={() => void act(c, "decline")}>{t("share.decline")}</Button>
              <Button icon={<ShieldCheck aria-hidden className="size-4" />} onClick={() => setOpen(c.id)}>{t("share.allow")}</Button>
            </div>
          )}
        </Card>
      ))}

      <h2 className="font-semibold">{t("share.active")}</h2>
      {list && active.length === 0 ? <p className="text-small text-bb-muted">{t("share.no_active")}</p> : null}
      {active.map((c) => (
        <Card key={c.id} className="flex flex-col gap-2">
          {head(c)}
          <p className="text-small">{t("share.valid_until", { date: day(c.valid_until, lang) })} · {t("share.viewed", { n: formatNumber(String(c.read_count), lang) })}</p>
          <p className="text-small">{t("share.showing")}: {(c.approved_sections ?? []).map((s) => t(`section.${s}`)).join(", ")}</p>
          {c.latest_report ? (
            <p className="break-all text-caption text-bb-muted">
              {t("share.version", { n: c.latest_report.version })} · SHA-256 {shortHash(c.latest_report.snapshot_sha256)}
            </p>
          ) : null}
          {c.review_status ? <p className="text-small">{t("share.review_status")}: {t(`review.${c.review_status}`)}</p> : null}
          <Activity c={c} />
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" busy={busy === `${c.id}:reshare`} icon={<Send aria-hidden className="size-4" />}
                    onClick={() => void act(c, "reshare")}>{t("share.reshare")}</Button>
            <Button variant="danger" busy={busy === `${c.id}:revoke`} icon={<Ban aria-hidden className="size-4" />}
                    onClick={() => void act(c, "revoke")}>{t("share.revoke")}</Button>
          </div>
          <p className="text-caption text-bb-muted">{t("share.reshare_note")}</p>
        </Card>
      ))}

      {closed.length > 0 ? (
        <>
          <h2 className="font-semibold">{t("share.closed")}</h2>
          {closed.map((c) => (
            <Card key={c.id} className="flex flex-col gap-1 opacity-80">
              {head(c)}
              <p className="text-small">{t(`consent.status.${c.is_expired && c.status === "approved" ? "expired" : c.status}`)}</p>
              {c.decision ? <Activity c={c} /> : null}
            </Card>
          ))}
        </>
      ) : null}
    </PageShell>
  );
}
