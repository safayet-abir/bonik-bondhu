import { ChevronRight, LogOut, Plus, Sprout, Store } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Profile } from "../../api/types";
import { Photo } from "../../components/Brand";
import { Button } from "../../components/Button";
import { DemoBadge } from "../../components/DemoBadge";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { useAuth } from "../../state/Auth";

export function ProfileIcon({ type, className = "size-6" }: { type: Profile["activity_type"]; className?: string }) {
  return type === "shop" ? <Store aria-hidden className={className} /> : <Sprout aria-hidden className={className} />;
}

/** SCR-O01 chooser. Right after login: 0 profiles -> create, 1 -> its home,
 *  ≥2 -> choose (App flow §1). Opened later via "Switch", it always lists. */
export function Profiles() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const fromLogin = Boolean((useLocation().state as { fromLogin?: boolean } | null)?.fromLogin);
  const { logout } = useAuth();
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<{ items: Profile[] }>("/profiles")
      .then(({ items }) => {
        if (items.length === 0) void navigate("/profiles/new", { replace: true });
        else if (items.length === 1 && fromLogin) void navigate(`/p/${items[0].id}/home`, { replace: true });
        else setProfiles(items);
      })
      .catch(setError);
  }, [navigate, fromLogin]);

  if (error) return <PageShell><ErrorBanner error={error} /></PageShell>;
  if (!profiles) return <Loading />;

  return (
    <PageShell title={t("profiles.which")} aside={<LanguageSwitch tone="wall" />}>
      <ul className="flex flex-col gap-3">
        {profiles.map((p) => (
          <li key={p.id}>
            <Link
              to={`/p/${p.id}/home`}
              className="flex min-h-16 items-center gap-3 overflow-hidden rounded-xl bb-hard-sm bg-bb-surface pr-4 transition-transform duration-100 hover:-translate-y-0.5"
            >
              {/* the business's own world: a shop front or a paddy field */}
              <span className="relative h-20 w-24 shrink-0 border-r-2 border-bb-iron">
                <Photo slug={p.activity_type === "shop" ? "shop-keraniganj" : "paddy-path"} decorative />
                <span className="absolute bottom-1.5 left-1.5 flex size-8 items-center justify-center rounded-md bg-bb-surface/95 text-bb-primary">
                  <ProfileIcon type={p.activity_type} className="size-5" />
                </span>
              </span>
              <span className="flex-1">
                <span className="block font-semibold">{p.display_name}</span>
                <span className="text-small text-bb-muted">{t(`profile.type.${p.activity_type}`)}</span>
              </span>
              {p.is_demo ? <DemoBadge /> : null}
              <ChevronRight aria-hidden className="size-5 text-bb-muted" />
            </Link>
          </li>
        ))}
      </ul>
      <Button variant="secondary" full icon={<Plus aria-hidden className="size-5" />}
              onClick={() => navigate("/profiles/new")}>
        {t("profiles.add")}
      </Button>
      <Button variant="secondary" full icon={<LogOut aria-hidden className="size-5" />}
              onClick={() => void logout().then(() => navigate("/login"))}>
        {t("auth.logout")}
      </Button>
    </PageShell>
  );
}
