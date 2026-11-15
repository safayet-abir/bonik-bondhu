"""Database engine and per-request transaction (TRD §4 "Transactions")."""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .core.errors import AppError


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        hide_parameters=True,  # DB error text (logged on 500s) must not carry phones, emails or amounts
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=True, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """One DB transaction per request: commit on success, roll back on any
    exception, so there are never partial writes. An AppError raised with
    commit=True (e.g. a failed login that must still record the failure
    counter and audit row) commits before the error response is sent."""
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except AppError as exc:
        if exc.commit:
            db.commit()
        else:
            db.rollback()
        raise
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


# scope="function": the commit happens BEFORE the response is sent, so a
# client never sees 201 for a write that later failed to commit.
DbSession = Annotated[Session, Depends(get_db, scope="function")]
