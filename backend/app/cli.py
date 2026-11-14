"""Admin CLI — never exposed over HTTP (DEC-24, SUG-29).

    python -m app.cli create-lender --org "DEMO Bank Ltd (fictional)" --org-type bank \
        --name "Nasrin Officer" --phone 01900000101 --email nasrin@example.com [--designation "SME Officer"]
    python -m app.cli reset-password --phone 01712345678

Passwords are typed at a hidden prompt (or read from BB_NEW_PASSWORD for
scripted use) and never echoed or logged.

    python -m app.cli seed-demo     # fictional DEMO data; password from DEMO_PASSWORD
    python -m app.cli reset-demo    # delete DEMO rows (audit rows stay) and seed again

    python -m app.cli import-news ../data/news/curated_news.csv
        # validate rows, upsert by dedup_key; rejected rows are reported (exit 1)
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import func, select, update

from . import demo
from .config import get_settings
from .core.audit import audit
from .core.clock import today, utcnow
from .core.security import hash_password, normalize_phone, password_problem
from .db import get_sessionmaker
from .models import LenderOfficer, LenderOrganization, User, UserSession
from .services import news_service


def _read_password(phone: str) -> str:
    pw = os.environ.get("BB_NEW_PASSWORD")
    if pw is None:
        pw = getpass.getpass("Temporary password: ")
        if getpass.getpass("Repeat password: ") != pw:
            sys.exit("Passwords do not match.")
    if problem := password_problem(pw, phone):
        sys.exit(f"Password rejected ({problem}). Use 8–128 chars, not only digits, not the phone number.")
    return pw


def create_lender(args: argparse.Namespace) -> int:
    phone = normalize_phone(args.phone)
    if phone is None:
        sys.exit("Invalid Bangladesh mobile number.")
    email = args.email.strip().lower()
    password = _read_password(phone)
    with get_sessionmaker()() as db, db.begin():
        if db.scalar(select(User.id).where(User.phone_e164 == phone)):
            sys.exit("A user with this phone already exists.")
        if db.scalar(select(User.id).where(func.lower(User.email) == email)):
            sys.exit("A user with this email already exists.")
        org = db.scalar(select(LenderOrganization).where(LenderOrganization.name == args.org))
        if org is None:
            org = LenderOrganization(name=args.org, org_type=args.org_type, is_demo=args.demo)
            db.add(org)
            db.flush()
        user = User(full_name=args.name, phone_e164=phone, email=email,
                    password_hash=hash_password(password), role="lender_officer", is_demo=args.demo)
        db.add(user)
        db.flush()
        db.add(LenderOfficer(user_id=user.id, organization_id=org.id, designation=args.designation))
        audit(db, "admin.create_lender", actor_role="admin", entity_type="user", entity_id=user.id,
              lender_organization_id=org.id)
    print(f"Lender officer created in '{args.org}'. They can log in with phone {phone}.")
    return 0


def reset_password(args: argparse.Namespace) -> int:
    """Only after an offline identity check (DEC-21). Revokes all sessions."""
    phone = normalize_phone(args.phone)
    if phone is None:
        sys.exit("Invalid Bangladesh mobile number.")
    password = _read_password(phone)
    now = utcnow()
    with get_sessionmaker()() as db, db.begin():
        user = db.scalar(select(User).where(User.phone_e164 == phone))
        if user is None:
            sys.exit("No user with this phone.")
        user.password_hash = hash_password(password)
        user.failed_login_count = 0
        user.locked_until = None
        db.execute(update(UserSession)
                   .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
                   .values(revoked_at=now))
        audit(db, "admin.reset_password", actor_role="admin", entity_type="user", entity_id=user.id)
    print("Password reset; all existing sessions were logged out.")
    return 0


def _demo_password() -> str:
    pw = os.environ.get("DEMO_PASSWORD") or get_settings().DEMO_PASSWORD
    if not pw:
        sys.exit("Set DEMO_PASSWORD (environment or backend/.env) before seeding DEMO data.")
    if password_problem(pw, "+8801900000001"):
        sys.exit("DEMO_PASSWORD rejected: use 8–128 chars, not only digits.")
    return pw


def seed_demo_cmd(args: argparse.Namespace) -> int:
    pw = _demo_password()
    with get_sessionmaker()() as db, db.begin():
        conn = db.connection()
        if demo.demo_present(conn):
            sys.exit("DEMO data (or a user with a DEMO phone) already exists. Run reset-demo instead.")
        n = demo.seed(conn, pw)
    print(f"DEMO data seeded ({n} demo users; password = DEMO_PASSWORD). All data is fictional.")
    return 0


def reset_demo_cmd(args: argparse.Namespace) -> int:
    pw = _demo_password()
    with get_sessionmaker()() as db, db.begin():
        conn = db.connection()
        demo.reset(conn)
        n = demo.seed(conn, pw)
        audit(db, "admin.reset_demo", actor_role="admin", entity_type="demo")
    print(f"DEMO data deleted and re-seeded ({n} demo users). Audit rows are kept.")
    return 0


def import_news_cmd(args: argparse.Namespace) -> int:
    path = Path(args.csv)
    if not path.is_file():
        sys.exit(f"File not found: {path}")
    with get_sessionmaker()() as db, db.begin():
        report = news_service.import_csv(db, path, today())
    print(f"News import: {report.inserted} inserted, {report.updated} updated, {len(report.rejected)} rejected.")
    for line, reason in report.rejected:
        print(f"  line {line}: {reason}")
    return 1 if report.rejected else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Bonik Bondhu admin commands")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-lender", help="create a lender officer (and organisation if new)")
    p.add_argument("--org", required=True, help="lender organisation name")
    p.add_argument("--org-type", default="bank", choices=["bank", "mfi", "ngo", "other"])
    p.add_argument("--name", required=True, help="officer full name")
    p.add_argument("--phone", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--designation")
    p.add_argument("--demo", action="store_true", help="mark organisation/officer as DEMO data")
    p.set_defaults(func=create_lender)

    p = sub.add_parser("reset-password", help="reset a user's password after offline identity check")
    p.add_argument("--phone", required=True)
    p.set_defaults(func=reset_password)

    p = sub.add_parser("seed-demo", help="insert fictional DEMO data (db/seed_demo.sql)")
    p.set_defaults(func=seed_demo_cmd)

    p = sub.add_parser("reset-demo", help="delete all DEMO rows and seed them again")
    p.set_defaults(func=reset_demo_cmd)

    p = sub.add_parser("import-news", help="import curated news events from a CSV file")
    p.add_argument("csv", help="path to curated_news.csv")
    p.set_defaults(func=import_news_cmd)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
