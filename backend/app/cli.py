"""Admin CLI — never exposed over HTTP (DEC-24, SUG-29).

    python -m app.cli create-lender --org "DEMO Bank Ltd (fictional)" --org-type bank \
        --name "Nasrin Officer" --phone 01900000101 --email nasrin@example.com [--designation "SME Officer"]
    python -m app.cli reset-password --phone 01712345678

Passwords are typed at a hidden prompt (or read from BB_NEW_PASSWORD for
scripted use) and never echoed or logged. Later phases add seed-demo,
reset-demo (P3-T09) and import-news (P4-T04).
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import func, select, update

from .core.audit import audit
from .core.clock import utcnow
from .core.security import hash_password, normalize_phone, password_problem
from .db import get_sessionmaker
from .models import LenderOfficer, LenderOrganization, User, UserSession


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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
