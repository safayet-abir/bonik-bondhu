"""Money summary for a date range (FR-LED-08/09) using engine.accounting."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.clock import today
from ..core.errors import field_error
from ..engine.accounting import OPERATING_TYPES, Txn, summarize
from ..models import BusinessProfile, Transaction
from ..schemas.ledger import EvidenceMix, RecordCoverage, SummaryOut


def _pct(part: int, whole: int) -> str:
    return f"{(Decimal(part) * 100 / whole):.1f}" if whole else "0.0"


def record_coverage(db: Session, profile: BusinessProfile, as_of: date) -> RecordCoverage:
    """Complete 7-day blocks ending yesterday that contain at least one
    confirmed operating record. Shown as plain coverage, never a score (DEC-13)."""
    weeks = get_settings().FORECAST_WINDOW_WEEKS
    start = as_of - timedelta(days=7 * weeks)
    dates = db.scalars(
        select(Transaction.value_date).distinct().where(
            Transaction.profile_id == profile.id,
            Transaction.status == "confirmed",
            Transaction.txn_type.in_(OPERATING_TYPES),
            Transaction.value_date >= start,
            Transaction.value_date < as_of,
        )
    )
    # Block k covers [as_of-7k, as_of-7k+6], i.e. days_ago in 7k-6..7k -> k = ceil(days_ago/7)
    blocks = {((as_of - d).days + 6) // 7 for d in dates}
    return RecordCoverage(weeks_with_records=len(blocks), window_weeks=weeks)


def summary(db: Session, profile: BusinessProfile, from_: date | None, to: date | None) -> SummaryOut:
    t = today()
    to = to or t
    from_ = from_ or to.replace(day=1)  # default: current month
    if from_ > to:
        raise field_error("from", "err.field.date_range")

    rows = db.execute(
        select(Transaction.txn_type, Transaction.amount, Transaction.value_date,
               Transaction.evidence_state)
        .where(Transaction.profile_id == profile.id, Transaction.status == "confirmed",
               Transaction.value_date <= to)
    ).all()
    in_range = [r for r in rows if r.value_date >= from_]
    period = summarize(Txn(r.txn_type, r.amount) for r in in_range)
    # Outstanding receivables/payables are all-time up to `to` (API spec §4.4).
    all_time = summarize(Txn(r.txn_type, r.amount) for r in rows)
    period["receivables_outstanding"] = all_time["receivables_outstanding"]
    period["payables_outstanding"] = all_time["payables_outstanding"]

    attached = sum(1 for r in in_range if r.evidence_state == "document_attached")
    return SummaryOut(
        from_=from_,
        to=to,
        has_data=bool(in_range),
        **period,
        evidence_mix=EvidenceMix(
            declared_pct=_pct(len(in_range) - attached, len(in_range)),
            document_attached_pct=_pct(attached, len(in_range)),
        ),
        record_coverage=record_coverage(db, profile, t),
    )
