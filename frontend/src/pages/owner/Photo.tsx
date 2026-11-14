import { Camera, PenLine, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, ApiError } from "../../api/client";
import type { DocumentOut, ExtractionDraft } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { useActiveProfile } from "../../state/ActiveProfile";

const UNSURE = 0.8; // UI-only threshold (UI spec SCR-O05)

/** SCR-O05 Entry from a receipt photo (FR-EXT-01..05). The photo is always
 *  kept as evidence; reading it with AI is optional and needs consent for this
 *  upload. Nothing is saved until the owner checks and confirms the entry form. */
export function Photo() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState<"ai" | "manual" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const back = `/p/${p.id}/entries`;

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function pick(f: File | null) {
    setFile(f);
    setError(null);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function go(useAi: boolean) {
    if (!file) return;
    setBusy(useAi ? "ai" : "manual");
    setError(null);
    const q = new URLSearchParams({ back });
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("purpose", "receipt");
      const doc = await api<DocumentOut>(`/profiles/${p.id}/documents`, { method: "POST", body: form });
      q.set("doc", doc.id);
      if (doc.duplicate_of) q.set("dup", "1");
      if (useAi) {
        try {
          const d = await api<ExtractionDraft>(`/profiles/${p.id}/extraction-drafts`,
                                               { method: "POST", body: { document_id: doc.id, ai_consent: true } });
          const f = d.proposed;
          q.set("draft", d.id);
          q.set("type", f.txn_type.value ?? "unknown");
          if (f.amount.value) q.set("amount", f.amount.value);
          if (f.value_date.value) q.set("date", f.value_date.value);
          if (f.note.value) q.set("note", f.note.value);
          if (d.matched_supplier_id) q.set("supplier_id", d.matched_supplier_id);
          const unsure = (["amount", "value_date"] as const).filter((k) => f[k].confidence < UNSURE);
          if (unsure.length) q.set("low", unsure.join(","));
        } catch (err) {
          // FR-EXT-04: AI off, failed or over the daily limit -> manual form, photo still attached
          q.set("notice", err instanceof ApiError ? err.messageKey : "ai.err.unavailable");
        }
      }
      void navigate(`/p/${p.id}/entries/new?${q}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageShell title={t("photo.title")} back={back}>
      <ErrorBanner error={error} />
      <label className="flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-bb border border-dashed border-bb-primary bg-bb-surface p-4 font-semibold text-bb-primary">
        <Camera aria-hidden className="size-5" />
        {file ? t("photo.change") : t("photo.pick")}
        <input type="file" accept="image/jpeg,image/png" capture="environment" className="sr-only"
               onChange={(e) => pick(e.target.files?.[0] ?? null)} />
      </label>
      {preview ? (
        <img src={preview} alt={t("photo.preview")} className="max-h-80 w-full rounded-bb border border-bb-border object-contain" />
      ) : null}
      <p className="text-small text-bb-muted">{t("photo.hint")}</p>
      <label className="flex items-start gap-3 rounded-bb border border-bb-border bg-bb-surface p-3">
        <input type="checkbox" className="mt-1 size-5 shrink-0" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>
          {t("photo.ai_consent")}
          <span className="block text-small text-bb-muted">{t("photo.ai_consent_detail")}</span>
        </span>
      </label>
      <Button full busy={busy === "ai"} disabled={!file || !consent || busy !== null}
              icon={<Sparkles aria-hidden className="size-5" />} onClick={() => void go(true)}>
        {t("photo.read_ai")}
      </Button>
      <Button full variant="secondary" busy={busy === "manual"} disabled={!file || busy !== null}
              icon={<PenLine aria-hidden className="size-5" />} onClick={() => void go(false)}>
        {t("photo.manual")}
      </Button>
    </PageShell>
  );
}
