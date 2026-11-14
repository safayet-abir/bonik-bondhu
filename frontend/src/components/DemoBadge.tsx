import { useTranslation } from "react-i18next";

/** Shown on every DEMO profile, lender and news item (FR-DEMO-01). */
export function DemoBadge() {
  const { t } = useTranslation();
  return (
    <span className="rounded-full bg-bb-demo px-2 py-0.5 text-caption font-semibold text-white">
      {t("demo.badge")}
    </span>
  );
}
