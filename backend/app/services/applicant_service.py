"""F5: private owner declarations, explicitly opted into each new snapshot.

NID is stored as text (SUG-63 option b); no field-level encryption is claimed.
Never include request values in exceptions, audit metadata or AI tools.
"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..core.clock import utcnow
from ..core.errors import field_error
from ..models.applicant import ApplicantDetails
from ..schemas.applicant import ApplicantIn, FIELDS, REQUIRED


def get(db: Session, profile):
    return db.scalar(select(ApplicantDetails).where(ApplicantDetails.profile_id == profile.id))


def completeness(row):
    missing = [key for key in REQUIRED if row is None or getattr(row, key) is None]
    completed = len(REQUIRED) - len(missing)
    return {"completed": completed, "total": len(REQUIRED), "percent": completed * 100 // len(REQUIRED), "missing": missing}


def masked(row):
    body = {key: getattr(row, key) if row else None for key in FIELDS if key not in ("nid_number", "date_of_birth")}
    return {**body, "nid_masked": ("•••• " + row.nid_number[-4:]) if row and row.nid_number else None,
            "has_date_of_birth": bool(row and row.date_of_birth),
            "declared_at": row.declared_at.isoformat() if row else None,
            "label_key": "applicant.declared", "completeness": completeness(row)}


def upsert(db: Session, user, profile, data: ApplicantIn, request=None):
    values = {key: getattr(data, key) for key in data.model_fields_set}
    if not values:
        return get(db, profile)
    now = utcnow()
    stmt = insert(ApplicantDetails).values(profile_id=profile.id, **values, declared_at=now, updated_at=now)
    db.execute(stmt.on_conflict_do_update(index_elements=[ApplicantDetails.profile_id],
               set_={**values, "declared_at": now, "updated_at": now}))
    # Identity edits do not change cash-flow inputs or existing immutable reports.
    audit(db, "applicant.update", request=request, actor_user_id=user.id, actor_role="owner",
          entity_type="business_profile", entity_id=profile.id, profile_id=profile.id)
    db.flush()
    db.expire_all()
    return get(db, profile)


def snapshot(db: Session, profile):
    row = get(db, profile)
    if completeness(row)["missing"]:
        raise field_error("approved_sections", "applicant.err.missing")
    return {**{key: (getattr(row, key).isoformat() if key == "date_of_birth" else getattr(row, key))
               for key in FIELDS}, "declared_at": row.declared_at.isoformat(), "label_key": "applicant.declared"}
