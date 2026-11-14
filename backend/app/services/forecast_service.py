"""Forecast baseline runs for shop profiles (FR-FC-01..06; Architecture §5.1).
The numbers are a rolling average of the owner's own records — an estimate,
not a prediction model and never guaranteed income."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.clock import today
from ..engine import baseline as bl
from ..engine.money import money
from ..engine.schedules import HORIZON_DAYS, horizon_end
from ..models import BusinessProfile, ForecastRun, Transaction
from ..schemas.forecast import ForecastOut, WeekOut, Weekly, WeeklyNet
from . import debt_service


def resolve_as_of(as_of: date | None) -> date:
    """Client-supplied as-of dates are a test/demo hook, ignored in production."""
    if as_of is None or get_settings().is_production:
        return today()
    return as_of


def compute(db: Session, profile: BusinessProfile, as_of: date) -> bl.Baseline:
    s = get_settings()
    start = as_of - timedelta(days=7 * s.FORECAST_WINDOW_WEEKS)
    rows = db.execute(
        select(Transaction.value_date, Transaction.txn_type, Transaction.amount).where(
            Transaction.profile_id == profile.id, Transaction.status == "confirmed",
            Transaction.txn_type.in_(bl.RECORD_TYPES),
            Transaction.value_date >= start, Transaction.value_date < as_of)
    ).all()
    blocks = bl.weekly_blocks(as_of, [(r.value_date, r.txn_type, r.amount) for r in rows], s.FORECAST_WINDOW_WEEKS)
    return bl.weekly_baseline(blocks, s.FORECAST_WINDOW_WEEKS, s.FORECAST_MIN_WEEKS)


def _q(x: Decimal | None) -> Decimal | None:
    return None if x is None else money(x)


def create_run(db: Session, profile: BusinessProfile, as_of: date, b: bl.Baseline | None = None) -> ForecastRun:
    s = get_settings()
    b = b or compute(db, profile, as_of)
    debt_rows = [r for _, rows in debt_service.obligation_rows(db, profile, as_of, horizon_end(as_of)) for r in rows]
    ok = b.ok
    run = ForecastRun(
        profile_id=profile.id, as_of_date=as_of, method_version=bl.METHOD_VERSION, status=b.status,
        window_weeks=s.FORECAST_WINDOW_WEEKS, weeks_with_records=b.weeks_used, min_weeks_required=s.FORECAST_MIN_WEEKS,
        net_weekly_expected=_q(b.net_weekly_expected) if ok else None,
        net_weekly_low=_q(b.net_weekly_low) if ok else None,
        net_weekly_high=_q(b.net_weekly_high) if ok else None,
        collections_weekly_expected=_q(b.collections_weekly_expected) if ok else None,
        payments_weekly_expected=_q(b.payments_weekly_expected) if ok else None,
        purchases_weekly_expected=_q(b.purchases_weekly_expected) if ok else None,
        horizons=bl.horizons(b, as_of, debt_rows),
        assumptions={
            "weeks": [{"start": w.start.isoformat(), "end": w.end.isoformat(), "has_records": w.has_records,
                       "net": f"{money(w.collections - w.payments):.2f}" if w.has_records else None}
                      for w in b.blocks],
            "horizon_days": HORIZON_DAYS,
            "missing_weeks_are_not_zero": True,
            "excluded": ["loans", "owner_withdrawals", "owner_contributions", "credit_sales_until_collected"],
        },
        profile_data_version=profile.data_version,
    )
    db.add(run)
    db.flush()
    db.refresh(run)
    return run


def latest(db: Session, profile: BusinessProfile) -> ForecastRun | None:
    return db.scalar(select(ForecastRun).where(ForecastRun.profile_id == profile.id)
                     .order_by(ForecastRun.created_at.desc(), ForecastRun.id).limit(1))


def is_stale(run: ForecastRun, profile: BusinessProfile) -> bool:
    return run.profile_data_version != profile.data_version


def forecast_out(run: ForecastRun, profile: BusinessProfile) -> ForecastOut:
    weekly = None
    if run.status == "ok":
        weekly = Weekly(
            net=WeeklyNet(low=run.net_weekly_low, expected=run.net_weekly_expected, high=run.net_weekly_high),
            collections_expected=run.collections_weekly_expected, payments_expected=run.payments_weekly_expected,
            purchases_expected=run.purchases_weekly_expected,
        )
    weeks = [WeekOut(start=w["start"], end=w["end"], has_records=w["has_records"],
                     net=Decimal(w["net"]) if w["net"] is not None else None)
             for w in run.assumptions.get("weeks", [])]
    return ForecastOut(
        id=run.id, status=run.status, as_of_date=run.as_of_date, method_version=run.method_version,
        weeks_with_records=run.weeks_with_records, window_weeks=run.window_weeks,
        min_weeks_required=run.min_weeks_required, weekly=weekly, horizons=run.horizons, weeks=weeks,
        is_stale=is_stale(run, profile), created_at=run.created_at,
    )
