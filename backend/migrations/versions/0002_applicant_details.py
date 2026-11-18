"""Add optional applicant details without changing existing financial records.

The initial migration reads its frozen 0001 schema. Both a fresh install and an
existing 0001 database therefore follow the same migration chain.
"""
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "0002_applicant_details"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

OLD_SECTIONS = (
    "profile_summary", "money_summary", "forecast", "financing_request", "obligations",
    "supplier_risk", "news_signals", "season_summary", "transaction_list",
)


def _sections(sections):
    # Trusted constants only. Preserve the original cardinality and required-section checks.
    bind = op.get_bind()
    checks = bind.execute(text("""SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint WHERE conrelid = 'consents'::regclass AND contype = 'c'""")).all()
    for name, definition in checks:
        if "<@" in definition and ("requested_sections" in definition or "approved_sections" in definition):
            op.drop_constraint(name, "consents", type_="check")
    allowed = "ARRAY[" + ",".join("'" + s + "'" for s in sections) + "]::text[]"
    op.create_check_constraint("consents_requested_sections_check", "consents",
                               "cardinality(requested_sections) >= 1 AND requested_sections <@ " + allowed)
    op.create_check_constraint("consents_approved_sections_check", "consents", "approved_sections <@ " + allowed)


def upgrade():
    sql = (Path(__file__).resolve().parents[2] / "db" / "applicant_0002.sql").read_text(encoding="utf-8")
    op.execute(text(sql))
    _sections((*OLD_SECTIONS, "applicant_details"))


def downgrade():
    # Never silently destroy applicant records or invalidate already shared snapshots.
    bind = op.get_bind()
    populated = bind.execute(text("""SELECT EXISTS(SELECT 1 FROM applicant_details)
        OR EXISTS(SELECT 1 FROM consents WHERE 'applicant_details' = ANY(requested_sections)
          OR 'applicant_details' = ANY(approved_sections))""")).scalar()
    if populated:
        raise RuntimeError("F5 data exists: use the compatible recovery build; destructive downgrade refused")
    _sections(OLD_SECTIONS)
    op.drop_table("applicant_details")
