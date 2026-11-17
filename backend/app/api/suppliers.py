"""/profiles/{pid}/suppliers (API spec §4.6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from ..core.clock import today
from ..core.deps import OwnedProfile, ShopProfile
from ..db import DbSession
from ..schemas.supplier import ConcentrationOut, SupplierCreate, SupplierList, SupplierOut, SupplierPatch
from ..services import graph_service, supplier_service

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


concentration_router = APIRouter(prefix="/profiles/{pid}", tags=["suppliers"])


@concentration_router.get("/supplier-concentration", response_model=ConcentrationOut)
def supplier_concentration(profile: OwnedProfile, db: DbSession) -> ConcentrationOut:
    """API #24 (FR-SUP-03..06). Window ends yesterday (Asia/Dhaka)."""
    return supplier_service.concentration_out(supplier_service.concentration(db, profile, today()))


@concentration_router.get("/supply-graph")
def supply_graph(profile: OwnedProfile, db: DbSession) -> dict:
    """Plan Ultra F4: business → suppliers → areas / goods → news, with the purchase share through each node."""
    return graph_service.supply_graph(db, profile, today())


@concentration_router.get("/supply-graph/whatif")
def supply_graph_whatif(profile: ShopProfile, db: DbSession, node: str = Query(max_length=300),
                        days: int = 7) -> dict:
    """If supply through `node` stops for 7 or 14 days, on the latest check's inputs. Read-only, never stored."""
    return graph_service.whatif(db, profile, node, days, today())
