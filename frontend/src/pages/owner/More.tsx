import { ArrowLeftRight, LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../state/Auth";

/** "More" menu + SCR-O16 settings (language, switch profile, logout).
 *  Suppliers, debts, forecast and sharing are added as their phases land. */
export function More() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { me, logout } = useAuth();
  return (
    <PageShell title={t("nav.more")}>
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
