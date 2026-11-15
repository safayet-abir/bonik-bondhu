"""E10 measurement (P6-T08; AI doc §8.5): 20 gold questions (10 bn + 10 en) through the REAL
production advisor (ai_service.advise: session-bound tools, grounding check, forbidden-phrase check,
template fallback, daily cap) on the DEMO seed in the dev database. Writes
tests/ai/reports/E10_report.md. Not a pytest test (needs network + key); no pass threshold.

    python -m app.cli reset-demo && python tests/ai/run_e10.py      (from backend/, PYTHONPATH=.)

Stores no chat text in the database (as in production); the report contains the questions and the
replies, which only describe fictional DEMO data. Prints no keys."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from sqlalchemy import select

from app.ai import advisor
from app.ai.grounding import BN_DIGITS, has_forbidden
from app.core.errors import AppError
from app.db import get_sessionmaker
from app.models import BusinessProfile, User
from app.schemas.ai import AdvisorIn
from app.core.clock import today
from app.services import ai_service, assessment_service, financing_service

HERE = Path(__file__).parent
PAUSE_S = 8  # free-tier requests per minute
CHECKED = ("Rahim Store", "Karim Variety Store", "Rahim Rice Farm")


def norm(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", text.translate(BN_DIGITS)).casefold()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    qs = json.loads((HERE / "e10_questions.json").read_text(encoding="utf-8"))["questions"]
    with get_sessionmaker()() as db, db.begin():  # as in the demo script, owners press "Check" first …
        for name in CHECKED:
            p = db.scalar(select(BusinessProfile).where(BusinessProfile.display_name == name,
                                                        BusinessProfile.is_demo.is_(True)))
            assessment_service.run(db, p, financing_service.list_requests(db, p)[0].id, today())
    rows = []  # … Selina Tailoring (D4) stays unchecked, so the advisor works its status out live
    for n, q in enumerate(qs):
        if n:
            time.sleep(PAUSE_S)
        with get_sessionmaker()() as db, db.begin():
            user = db.scalar(select(User).where(User.phone_e164 == "+88" + q["phone"]))
            profile = db.scalar(select(BusinessProfile).where(BusinessProfile.owner_user_id == user.id,
                                                              BusinessProfile.display_name == q["profile"]))
            try:
                out = ai_service.advise(db, user, profile, AdvisorIn(message=q["q"]))
            except AppError as exc:  # 503 / 429: the UI would show the help menu
                out = {"reply": "", "mode": exc.code, "grounded": False, "tools_used": [], "language": ""}
        text = norm(out["reply"])
        content = all(any(norm(alt) in text for alt in group) for group in q["must"]) if out["reply"] else False
        leak = [s for s in q.get("must_not", []) if norm(s) in text]
        row = {**q, **out, "content_ok": content, "leak": leak, "forbidden": has_forbidden(out["reply"]),
               "lang_ok": out.get("language") == q["lang"]}
        row["pass"] = out["mode"] == "llm" and content and not leak and not row["forbidden"] and row["lang_ok"]
        rows.append(row)
        print(f"{q['id']} {q['lang']} {q['kind']:<10} mode={out['mode']:<8} content={content} leak={leak} "
              f"-> {out['reply'][:110]!r}")
    write_report(rows)


def write_report(rows: list[dict]) -> None:
    n = len(rows)
    count = lambda f: sum(1 for r in rows if f(r))
    by = lambda lang: f"{count(lambda r: r['lang'] == lang and r['pass'])}/{count(lambda r: r['lang'] == lang)}"
    lines = [
        "# E10 — advisor gold questions, measured (P6-T08)", "",
        f"Run {time.strftime('%Y-%m-%d %H:%M')} · prompt `{advisor.PROMPT_NAME}` · production path "
        "`ai_service.advise` (Gemini first, Groq fallback) on the DEMO seed. Before the questions the "
        f"financing check was run for {', '.join(CHECKED)} (as in the demo script); Selina Tailoring was left "
        "unchecked.", "",
        f"N = {n} (10 Bangla, 10 English) · **passed {count(lambda r: r['pass'])}/{n}** "
        f"(bn {by('bn')}, en {by('en')})", "",
        "A question passes when the reply came from the LLM and passed the server's grounding check "
        "(`mode = llm`), contains the expected fact, is in the question's language, has no forbidden "
        "phrase and leaks nothing from another profile.", "",
        "| Check | Count |", "|---|---|",
        f"| LLM reply passed grounding (`mode = llm`) | {count(lambda r: r['mode'] == 'llm')}/{n} |",
        f"| replaced by the fixed answer (`mode = template`) | {count(lambda r: r['mode'] == 'template')}/{n} |",
        f"| AI unavailable / limit (help menu shown) | {count(lambda r: r['mode'] not in ('llm', 'template'))}/{n} |",
        f"| expected fact present | {count(lambda r: r['content_ok'])}/{n} |",
        f"| forbidden phrase in the final reply | {count(lambda r: r['forbidden'])}/{n} |",
        f"| cross-profile leak (isolation questions q05, q12) | {count(lambda r: bool(r['leak']))} |",
        f"| reply language = question language | {count(lambda r: r['lang_ok'])}/{n} |", "",
        "| id | profile | kind | question | mode | tools | fact | pass | reply |", "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        reply = r["reply"].replace("\n", " ").replace("|", "/")
        lines.append(f"| {r['id']} | {r['profile']} | {r['kind']} | {r['q']} | {r['mode']} | "
                     f"{', '.join(r['tools_used']) or '—'} | {'yes' if r['content_ok'] else 'no'} | "
                     f"{'✅' if r['pass'] else '❌'} | {reply} |")
    lines += ["", "Gold set written by the developer on fictional DEMO data; a small N measures behaviour, "
              "not accuracy on real owners' questions."]
    out = HERE / "reports" / "E10_report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main()
