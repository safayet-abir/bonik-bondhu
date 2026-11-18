"""Fresh installs, existing data upgrades and the non-destructive rollback boundary."""
import secrets
from pathlib import Path
from app import demo

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_0001_upgrade_preserves_existing_records(clean_db):
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.attributes["database_url"] = clean_db
    engine = create_engine(clean_db)
    try:
        command.downgrade(cfg, "0001_initial")
        with engine.begin() as conn:
            demo.seed(conn, secrets.token_urlsafe(24))
            before = conn.execute(text("SELECT count(*), sum(amount) FROM transactions")).one()
            # A pre-existing non-sensitive row must survive both migration and app recovery.
            conn.execute(text("INSERT INTO lender_organizations (name, org_type, is_demo) "
                              "VALUES ('F5 migration fixture', 'bank', true)"))
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM lender_organizations WHERE name='F5 migration fixture'")).scalar() == 1
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0002_applicant_details"
            assert conn.execute(text("SELECT count(*) FROM applicant_details")).scalar() == 0
            assert conn.execute(text("SELECT count(*), sum(amount) FROM transactions")).one() == before
        command.upgrade(cfg, "head")  # Recovery build startup: already current, no destructive work.
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
