"""E2 measurement (P6-T08; Testing §5): read each labelled receipt with the REAL provider using
the production prompt, adapter and validation (ai/extraction.py), compare with the label and write
tests/ai/reports/E2_report.md. Not a pytest test (needs network + key); no pass threshold.

    python tests/ai/run_e2.py <dir with r01.jpg …>     (from backend/, PYTHONPATH=.)

Calls the provider directly (same code path as ai_service.extract minus DB/caps), pausing between
receipts for free-tier rate limits. Prints and stores no keys and no raw model text."""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.ai import extraction
from app.ai.provider import AIUnavailable, image_part, json_object, providers

HERE = Path(__file__).parent
PAUSE_S = 5


def main(img_dir: Path) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads((HERE / "e2_receipts.json").read_text(encoding="utf-8"))["receipts"]
    p = providers("receipt_extraction")[0]
    rows, today = [], date(2026, 11, 15)
    for n, r in enumerate(data):
        if n:
            time.sleep(PAUSE_S)
        exp = r["expected"]
        try:
            reply = p.chat([{"role": "user", "content": [
                {"type": "text", "text": extraction.PROMPT},
                image_part((img_dir / f"{r['id']}.jpg").read_bytes(), "image/jpeg")]}], max_tokens=800)
            got = extraction.proposed(json_object(reply.text), today)
            ms, err = reply.latency_ms, ""
        except (AIUnavailable, ValueError) as exc:
            got, ms, err = None, 0, f"{type(exc).__name__}: {exc}"
        if got is None:
            rows.append({"id": r["id"], "style": r["style"], "failed": err})
            print(f"{r['id']} FAILED {err}")
            continue
        g = {k: got[k]["value"] for k in ("txn_type", "amount", "value_date")}
        ok = {"amount": g["amount"] is not None and Decimal(g["amount"]) == Decimal(exp["amount"]),
              "date": g["value_date"] == exp["value_date"], "type": g["txn_type"] == exp["txn_type"]}
        rows.append({"id": r["id"], "style": r["style"], "expected": exp, "got": g, "ok": ok, "ms": ms,
                     "low_conf": [k for k in ("amount", "value_date") if got[k]["confidence"] < 0.8],
                     "supplier": got["supplier_name"]["value"]})
        print(f"{r['id']} {'OK ' if all(ok.values()) else 'FIX'} {g} {ms} ms")
    write_report(rows, p)


def write_report(rows: list[dict], p) -> None:
    done = [r for r in rows if "ok" in r]
    n, N = len(done), len(rows)
    pct = lambda k: f"{sum(r['ok'][k] for r in done)}/{n} ({100 * sum(r['ok'][k] for r in done) / n:.0f}%)" if n else "—"
    fix = sum(not all(r["ok"].values()) for r in done)
    lines = [
        "# E2 — receipt extraction, measured (P6-T08)", "",
        f"Run {time.strftime('%Y-%m-%d %H:%M')} · provider `{p.name}` · model `{p.model}` · prompt "
        f"`{extraction.PROMPT_NAME}`",
        "", "**Set: SYNTHETIC.** 20 receipts rendered from `e2_receipts.json` (fictional DEMO names, printed / "
        "Bangla / handwritten-style fonts, rotated, blurred, faded, no date, discount, one prompt-injection text). "
        "No real customer receipts were used; results on real photos (camera angle, crumpled paper, real "
        "handwriting) are expected to be lower. Labels are one person's judgement (type is sometimes ambiguous).",
        "", f"N = {N} · failures (no usable draft) = {N - n}", "",
        "| Field | Exact match |", "|---|---|",
        f"| amount | {pct('amount')} |", f"| date | {pct('date')} |", f"| type | {pct('type')} |",
        f"| needed any correction (amount, date or type) | {fix}/{n} |", "",
        "| id | style | expected type · amount · date | AI type · amount · date | needs fix | unsure (<0.8) | ms |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "failed" in r:
            lines.append(f"| {r['id']} | {r['style']} | — | FAILED: {r['failed']} | — | — | — |")
            continue
        e, g = r["expected"], r["got"]
        bad = [k for k, v in r["ok"].items() if not v]
        lines.append(f"| {r['id']} | {r['style']} | {e['txn_type']} · {e['amount']} · {e['value_date']} | "
                     f"{g['txn_type']} · {g['amount']} · {g['value_date']} | {', '.join(bad) or '—'} | "
                     f"{', '.join(r['low_conf']) or '—'} | {r['ms']} |")
    lines += ["", "Every draft still needs the owner's confirmation before it becomes an entry (FR-EXT-03); "
              "these numbers describe how much typing the AI saves, not an accuracy guarantee."]
    out = HERE / "reports" / "E2_report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
