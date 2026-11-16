import { useTranslation } from "react-i18next";

/** Shown on every DEMO profile, lender and news item (FR-DEMO-01). */
export function DemoBadge() {
  const { t } = useTranslation();
  return (
    // a rubber stamp in iron ink on an enamel ground: reads on the teal wall and on white plates alike
    <span className="inline-block rounded-sm border-2 border-bb-iron bg-bb-enamel px-1.5 font-display text-caption font-semibold uppercase tracking-wide text-bb-iron">
      {t("demo.badge")}
    </span>
  );
}
