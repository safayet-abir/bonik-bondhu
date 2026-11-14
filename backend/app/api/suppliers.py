"""/profiles/{pid}/suppliers (API spec §4.6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from ..core.deps import OwnedProfile
from ..db import DbSession
from ..schemas.supplier import SupplierCreate, SupplierList, SupplierOut, SupplierPatch
from ..services import supplier_service

router = APIRouter(prefix="/profiles/{pid}/suppliers", tags=["suppliers"])


@router.get("", response_model=SupplierList)
def list_suppliers(profile: OwnedProfile, db: DbSession) -> SupplierList:
    rows = supplier_service.list_suppliers(db, profile)
    return SupplierList(items=[supplier_service.supplier_out(s) for s in rows], total=len(rows))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SupplierOut)
def create_supplier(data: SupplierCreate, profile: OwnedProfile, db: DbSession) -> SupplierOut:
    return supplier_service.supplier_out(supplier_service.create(db, profile, data))


@router.patch("/{sid}", response_model=SupplierOut)
def update_supplier(sid: uuid.UUID, patch: SupplierPatch, profile: OwnedProfile, db: DbSession) -> SupplierOut:
    return supplier_service.supplier_out(supplier_service.update(db, profile, sid, patch))
