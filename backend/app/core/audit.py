"""Append-only security/consent audit log (DB doc §5.21). Ledger writes are
not security events and are not audited."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AuditLog
from .security import sha256_hex


def client_ip(request: Request | None) -> str | None:
    return request.client.host if request and request.client else None


def hash_ip(ip: str | None) -> str | None:
    return sha256_hex(get_settings().SECRET_SALT + ip) if ip else None


def audit(
    db: Session,
    action: str,
    outcome: str = "success",
    *,
    request: Request | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    profile_id: uuid.UUID | None = None,
    lender_organization_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            outcome=outcome,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=entity_type,
            entity_id=entity_id,
            profile_id=profile_id,
            lender_organization_id=lender_organization_id,
            ip_sha256=hash_ip(client_ip(request)),
            metadata_=metadata or {},
        )
    )
