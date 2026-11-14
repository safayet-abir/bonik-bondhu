import { ArrowLeftRight, BarChart3, ChevronRight, Landmark, LogOut, Share2, TrendingUp, Truck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { PageShell } from "../../components/PageShell";
import { useActiveProfile } from "../../state/ActiveProfile";
import { useAuth } from "../../state/Auth";

/** "More" menu (UI spec §4.1/4.2) + SCR-O16 settings. Forecast and
 *  Sharing are added as their phases land; farms never get Forecast. */
export function More() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const p = useActiveProfile();
  const { me, logout } = useAuth();
  const base = `/p/${p.id}`;
  const links = [
    ...(p.activity_type === "shop" ? [
      { to: `${base}/summary`, icon: BarChart3, label: t("summary.title") },
      { to: `${base}/forecast`, icon: TrendingUp, label: t("forecast.title") },
    ] : []),
    { to: `${base}/debts`, icon: Landmark, label: t("debt.title") },
    { to: `${base}/suppliers`, icon: Truck, label: t("supplier.title") },
    { to: `${base}/sharing`, icon: Share2, label: t("share.title") },
  ];
  return (
    <PageShell title={t("nav.more")}>
      <ul className="divide-y divide-bb-border rounded-bb border border-bb-border bg-bb-surface">
        {links.map(({ to, icon: Icon, label }) => (
          <li key={to}>
            <Link to={to} className="flex min-h-14 items-center gap-3 px-4">
              <Icon aria-hidden className="size-5 text-bb-primary" />
              <span className="flex-1 font-semibold">{label}</span>
              <ChevronRight aria-hidden className="size-5 text-bb-muted" />
            </Link>
          </li>
        ))}
      </ul>
      <Card className="flex flex-col gap-1">
        <p className="font-semibold">{me?.full_name}</p>
        <p className="text-small text-bb-muted">{me?.phone}</p>
      </Card>
      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">{t("lang.label")}</h2>
        <LanguageSwitch large />
      </section>
      <Button variant="secondary" full icon={<ArrowLeftRight aria-hidden className="size-5" />}
              onClick={() => navigate("/profiles")}>
        {t("profiles.switch")}
      </Button>
      <Button variant="secondary" full icon={<LogOut aria-hidden className="size-5" />}
              onClick={() => void logout().then(() => navigate("/login"))}>
        {t("auth.logout")}
      </Button>
    </PageShell>
  );
}
