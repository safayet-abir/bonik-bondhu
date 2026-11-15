"""Deterministic answers (AI doc §8.4; FR-ADV-07). Used for the help chips,
when no LLM is available, and when an LLM reply fails the grounding check.
Built only from tool data, so every number is grounded by construction."""
from __future__ import annotations

from decimal import Decimal

from .grounding import BN_DIGITS
from .tools import Toolbox

QUICK = ("next_week_installments", "money_this_month", "forecast_status", "assessment_status",
         "supplier_dependency", "news_latest")
TOOL_FOR = {"get_upcoming_installments": "next_week_installments", "get_money_summary": "money_this_month",
            "get_latest_forecast": "forecast_status", "get_latest_assessment": "assessment_status",
            "get_scenarios": "assessment_status", "get_supplier_dependency": "supplier_dependency",
            "get_news_signals": "news_latest"}
TITLES = {
    "next_week_installments": ("আগামী ৭ দিনের কিস্তি", "Installments in the next 7 days"),
    "money_this_month": ("এই মাসের টাকার হিসাব", "Money this month"),
    "forecast_status": ("সামনের সপ্তাহগুলোর অনুমান", "Estimate for coming weeks"),
    "assessment_status": ("আমার অর্থায়ন যাচাইয়ের ফল", "My financing check"),
    "supplier_dependency": ("সরবরাহকারীর উপর নির্ভরতা", "Supplier dependency"),
    "news_latest": ("আমার এলাকার খবর", "News for my area"),
}
STATUS = {
    "ready_for_lender_review": ("আপনার প্রস্তাব ঋণদাতার পর্যালোচনার জন্য তৈরি",
                                "your proposal is ready for a lender to review"),
    "not_affordable_base_case": ("সাবধানী হিসাবে প্রস্তাবিত কিস্তি আপনার নগদ টাকায় মিলছে না",
                                 "in the careful case your proposed payments do not fit your cash"),
    "insufficient_information": ("কিছু তথ্য বাকি আছে", "some information is missing"),
}


# Reply when the model's answer used a forbidden phrase (often by repeating "approved?/eligible?" from the question)
LENDER_DECIDES = {
    "bn": "বণিক বন্ধু ঋণ দেয় না এবং কোনো স্কোর দেয় না। ঋণের সিদ্ধান্ত নেয় শুধু ঋণদাতা। "
          "আপনার নিজের প্রস্তাবের যাচাইয়ের ফল অর্থায়ন অংশে দেখুন।",
    "en": "Bonik Bondhu does not lend and gives no score. Only the lender decides on a loan. "
          "You can see the check of your own proposal under Financing.",
}


def tk(v: str | Decimal | None, lang: str) -> str:
    """South-Asian grouping (1,50,000), no ".00", Bangla digits in bn."""
    d = Decimal(v or 0)
    whole, _, frac = f"{abs(d):.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    text = ",".join(([head] if head else []) + groups + [tail]) + ("" if frac == "00" else "." + frac)
    text = ("-" if d < 0 else "") + text
    return "Tk " + (text.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")) if lang == "bn" else text)


def _n(x: int | str, lang: str) -> str:
    s = str(x)
    return s.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")) if lang == "bn" else s


def answer(key: str, tb: Toolbox, lang: str) -> str:
    bn = lang == "bn"
    if key == "next_week_installments":
        d = tb.data("get_upcoming_installments", {"days": 7})
        if d.get("error"):
            return "এখন তথ্য পাওয়া যাচ্ছে না।" if bn else "This information is not available now."
        parts = [f"আগামী ৭ দিনে জানা কিস্তি: {tk(d['existing_total'], lang)} ({_n(d['existing_count'], lang)}টি)।"
                 if bn else f"Known installments in the next 7 days: {tk(d['existing_total'], lang)} "
                            f"({d['existing_count']})."]
        if d["proposed_count"]:
            parts.append(f"আপনার প্রস্তাবিত নতুন ঋণের কিস্তি: {tk(d['proposed_total'], lang)} — এটি আপনার প্রস্তাব, "
                         "ঋণদাতার অফার নয়।" if bn else f"Your proposed new loan: {tk(d['proposed_total'], lang)} — "
                                                     "your proposal, not a lender offer.")
        if not d["debts_declared"]:
            parts.append("আপনার চলতি ঋণের কথা এখনো জানাননি (আরও → আমার ঋণ)।" if bn
                         else "You have not told us about your current loans yet (More → Loans I owe).")
        return " ".join(parts)
    if key == "money_this_month":
        d = tb.data("get_money_summary", {"period": "this_month"})
        if d.get("error"):
            return "এখন তথ্য পাওয়া যাচ্ছে না।" if bn else "This information is not available now."
        if not d["has_data"]:
            return "এই মাসে এখনো কোনো হিসাব লেখা হয়নি।" if bn else "No entries recorded this month yet."
        return (f"এই মাসে এ পর্যন্ত: বিক্রি লেখা {tk(d['sales_recorded'], lang)}, ব্যবসায় টাকা এসেছে "
                f"{tk(d['operating_cash_in'], lang)}, গেছে {tk(d['operating_cash_out'], lang)}, নিট "
                f"{tk(d['net_operating_cash'], lang)}।") if bn else (
            f"This month so far: sales recorded {tk(d['sales_recorded'], lang)}, business money in "
            f"{tk(d['operating_cash_in'], lang)}, out {tk(d['operating_cash_out'], lang)}, net "
            f"{tk(d['net_operating_cash'], lang)}.")
    if key == "forecast_status":
        if not tb.shop:
            return "খামারের জন্য সাপ্তাহিক অনুমান নেই; মৌসুমের হিসাব দেখুন।" if bn else \
                "Farm profiles have no weekly forecast; see your season summary."
        d = tb.data("get_latest_forecast")
        if d.get("status") != "ok":
            return (f"অনুমানের জন্য অন্তত {_n(d.get('weeks_needed', 4), lang)} সপ্তাহের হিসাব লাগবে; এখন আছে "
                    f"{_n(d.get('weeks_with_records', 0), lang)} সপ্তাহ।") if bn else (
                f"An estimate needs at least {d.get('weeks_needed', 4)} weeks of records; you have "
                f"{d.get('weeks_with_records', 0)}.")
        w, h = d["weekly_net"], d["horizons_days"]["30"]
        return (f"সাধারণ এক সপ্তাহে নিট টাকা {tk(w['low'], lang)} থেকে {tk(w['high'], lang)} (সাধারণত "
                f"{tk(w['expected'], lang)})। সাবধানী হিসাবে আগামী ৩০ দিনে {tk(h['low'], lang)}। এটি অনুমান, নিশ্চয়তা নয়।"
                ) if bn else (
            f"In a normal week your net cash is {tk(w['low'], lang)} to {tk(w['high'], lang)} (usually "
            f"{tk(w['expected'], lang)}). Careful case for the next 30 days: {tk(h['low'], lang)}. "
            "This is an estimate, not a promise.")
    if key == "assessment_status":
        d = tb.data("get_latest_assessment")
        if d.get("status_code") == "no_financing_request":
            return "আপনার এখনো কোনো অর্থায়নের অনুরোধ নেই (অর্থায়ন)।" if bn else \
                "You have no financing request yet (Financing)."
        if d.get("error"):
            return "এখন তথ্য পাওয়া যাচ্ছে না।" if bn else "This information is not available now."
        text = STATUS[d["status_code"]][0 if bn else 1]
        missing = len(d["missing"])
        extra = (f" বাকি তথ্য: {_n(missing, lang)}টি।" if bn else f" Missing items: {missing}.") if missing else ""
        note = " এটি আপনার নিজের প্রস্তাবের যাচাই, ঋণের সিদ্ধান্ত নয় — সিদ্ধান্ত নেবে ঋণদাতা।" if bn else \
            " This checks your own proposal; it is not a lending decision — the lender decides."
        return (f"সর্বশেষ যাচাই: {text}।" if bn else f"Latest check: {text}.") + extra + note
    if key == "supplier_dependency":
        if not tb.shop:
            return "সরবরাহকারীর হিসাব দোকানের জন্য।" if bn else "Supplier dependency is shown for shops."
        d = tb.data("get_supplier_dependency")
        if not d.get("suppliers"):
            return "এখনো কোনো সরবরাহকারীর কেনাকাটার তথ্য নেই।" if bn else "No supplier purchase data yet."
        top = d["suppliers"][0]
        text = (f"আপনার কেনাকাটার {_n(top['share_pct'], lang)}% যায় {top['label']}-এর কাছে।" if bn
                else f"{top['share_pct']}% of your purchases go to {top['label']}.")
        if d["high_dependency"]:
            text += " একজন সরবরাহকারীর উপর বেশি নির্ভরতা — তার সমস্যা হলে আপনার ব্যবসায় প্রভাব পড়তে পারে।" if bn else \
                " That is a high dependency on one supplier: a problem there can hit your business."
        return text
    if key == "news_latest":
        d = tb.data("get_news_signals")
        signals = d.get("signals") or []
        if not signals:
            return "এখন আপনার এলাকার সাথে মেলে এমন কোনো খবর আমাদের তালিকায় নেই।" if bn else \
                "No news in our list matches your area right now."
        lines = []
        for s in signals[:3]:
            tags = []
            if s["is_demo"]:
                tags.append("DEMO")
            if s["corroboration"] == "single_source":
                tags.append("একটি সূত্র" if bn else "one source")
            if s["collected_automatically"]:
                tags.append("স্বয়ংক্রিয়ভাবে সংগ্রহ" if bn else "collected automatically")
            when = _n(s["published"], lang)
            lines.append(f"• {s['headline']} — {s['source']} ({when}) জানিয়েছে" if bn
                         else f"• {s['headline']} — reported by {s['source']} on {when}")
            if tags:
                lines[-1] += f" [{', '.join(tags)}]"
        return "\n".join(lines)
    return ""
