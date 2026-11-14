import { ArrowLeft, SearchX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { PageShell } from "../components/PageShell";

export function NotFound() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <PageShell>
      <EmptyState
        icon={<SearchX className="size-10" />}
        message={t("err.not_found")}
        action={
          <Button variant="secondary" icon={<ArrowLeft aria-hidden className="size-5" />} onClick={() => navigate("/")}>
            {t("common.back")}
          </Button>
        }
      />
    </PageShell>
  );
}
