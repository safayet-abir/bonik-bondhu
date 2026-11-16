import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { ActivityType, Profile } from "../../api/types";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { ProfileIcon } from "./Profiles";

/** SCR-O02 (minimal): name + type now; location/category are optional and
 *  asked again only when the owner starts financing (FR-PROF-02/06). */
export function ProfileCreate() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [type, setType] = useState<ActivityType | null>(null);
  const [district, setDistrict] = useState("");
  const [upazila, setUpazila] = useState("");
  const [category, setCategory] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!type) {
      setFields({ activity_type: "profile.err.type" });
      return;
    }
    setBusy(true);
    setFields({});
    setError(null);
    try {
      const p = await api<Profile>("/profiles", {
        method: "POST",
        body: { display_name: name, activity_type: type, district, upazila, business_category: category },
      });
      void navigate(`/p/${p.id}/home`, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  const types: ActivityType[] = ["shop", "crop_farm"];
  return (
    <PageShell title={t("profiles.create_title")}>
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Field label={t("profile.name")} value={name} onChange={(e) => setName(e.target.value)}
               hint={t("profile.name_hint")} errorKey={fields.display_name} required />
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-semibold">{t("profile.type")}</legend>
          <div className="grid grid-cols-2 gap-3">
            {types.map((ty) => (
              <button key={ty} type="button" aria-pressed={type === ty} onClick={() => setType(ty)}
                      className={`flex min-h-16 flex-col items-center justify-center gap-1 rounded-bb border p-3 font-semibold ${
                        type === ty ? "border-bb-primary bg-bb-primary-soft text-bb-primary" : "border-bb-border bg-bb-surface"
                      }`}>
                <ProfileIcon type={ty} />
                {t(`profile.type.${ty}`)}
              </button>
            ))}
          </div>
          {fields.activity_type ? <p className="text-small text-bb-danger">{t(fields.activity_type)}</p> : null}
        </fieldset>
        <p className="border-t border-bb-border pt-3 text-small text-bb-muted">{t("profile.optional_now")}</p>
        <Field label={t("profile.district")} value={district} onChange={(e) => setDistrict(e.target.value)}
               hint={t("profile.district_hint")} errorKey={fields.district} />
        <Field label={t("profile.upazila")} value={upazila} onChange={(e) => setUpazila(e.target.value)}
               hint={t("profile.upazila_hint")} errorKey={fields.upazila} />
        <Field label={t("profile.category")} value={category} onChange={(e) => setCategory(e.target.value)}
               hint={t(type === "crop_farm" ? "profile.category_hint.farm" : "profile.category_hint")}
               errorKey={fields.business_category} />
        <Button type="submit" full busy={busy}>
          {t("common.save")}
        </Button>
      </form>
    </PageShell>
  );
}
