import { Send } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError, getHealth } from "../../api/client";
import type { AdvisorReply, HelpPayload } from "../../api/types";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { useActiveProfile } from "../../state/ActiveProfile";

type Msg = { role: "user" | "assistant"; text: string; mode?: "llm" | "template" | "help" };
const MAX_HISTORY = 12; // ≤ 6 turns, kept only in this page (the server stores no chat text)

/** SCR-O15 Advisor (FR-ADV-01..08). Answers come only from this profile's
 *  records; numbers are checked on the server. Without an LLM (or over the
 *  daily limit) the same quick questions give fixed answers from the records. */
export function Advisor() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [help, setHelp] = useState<HelpPayload | null>(null);
  const [aiOn, setAiOn] = useState(true);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<HelpPayload>(`/profiles/${p.id}/advisor/help-topics?lang=${lang}`).then(setHelp).catch(setError);
  }, [p.id, lang]);
  useEffect(() => {
    getHealth().then((h) => setAiOn(h.llm === "configured")).catch(() => setAiOn(true));
  }, []);

  async function send(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    const history = msgs.filter((m) => m.mode !== "help").slice(-MAX_HISTORY).map(({ role, text }) => ({ role, text }));
    setMsgs((m) => [...m, { role: "user", text: message }]);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const r = await api<AdvisorReply>(`/profiles/${p.id}/advisor/messages`, { method: "POST", body: { message, history } });
      setMsgs((m) => [...m, { role: "assistant", text: r.reply, mode: r.mode }]);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 503 || err.status === 429)) {
        const h = err.details.help_topics as HelpPayload | undefined;
        if (h) setHelp(h);
        if (err.status === 503) setAiOn(false);
        setMsgs((m) => [...m, { role: "assistant", text: t(err.messageKey), mode: "help" }]);
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t("advisor.title")}>
      <p className="text-small text-bb-muted">{t("advisor.footer")}</p>
      {!aiOn ? <StatusBanner tone="info" title={t("advisor.off")} /> : null}
      <ErrorBanner error={error} />

      <section aria-label={t("advisor.quick")} className="flex flex-wrap gap-2">
        {help?.quick.map((q) => (
          <button key={q.key} type="button"
                  onClick={() => setMsgs((m) => [...m, { role: "user", text: q.title }, { role: "assistant", text: q.answer, mode: "help" }])}
                  className="min-h-12 rounded-full border border-bb-primary bg-bb-surface px-3 text-small font-semibold text-bb-primary">
            {q.title}
          </button>
        ))}
      </section>

      {msgs.length > 0 ? (
        <ol aria-live="polite" className="flex flex-col gap-2">
          {msgs.map((m, i) => (
            <li key={i} className={m.role === "user"
              ? "max-w-[85%] self-end rounded-bb bg-bb-primary p-3 text-white"
              : "max-w-[90%] self-start rounded-xl bb-hard-sm bg-bb-surface p-3"}>
              {/* plain text only: replies are never rendered as HTML */}
              <p className="whitespace-pre-line">{m.text}</p>
              {m.role === "assistant" && m.mode ? (
                <p className="mt-1 text-caption text-bb-muted">{t(`advisor.mode.${m.mode}`)}</p>
              ) : null}
            </li>
          ))}
          {busy ? <li className="self-start text-bb-muted">{t("advisor.thinking")}</li> : null}
        </ol>
      ) : null}

      {aiOn ? (
        <form onSubmit={send} className="flex flex-col gap-2">
          <Field label={t("advisor.ask")} value={input} maxLength={500} onChange={(e) => setInput(e.target.value)}
                 hint={t("advisor.ask_hint")} />
          <Button type="submit" busy={busy} disabled={!input.trim()} icon={<Send aria-hidden className="size-5" />}>
            {t("advisor.send")}
          </Button>
        </form>
      ) : null}

      {help ? (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold">{t("advisor.topics")}</h2>
          {help.items.map((h) => (
            <details key={h.key} className="rounded-xl bb-hard-sm bg-bb-surface px-3">
              <summary className="flex min-h-12 cursor-pointer items-center font-semibold">{lang === "bn" ? h.title_bn : h.title_en}</summary>
              <p className="pb-3 text-small">{lang === "bn" ? h.body_bn : h.body_en}</p>
            </details>
          ))}
        </section>
      ) : null}
    </PageShell>
  );
}
