"""GET /api/v1/health — liveness + DB check (API spec §4.1)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from ..db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    llm = get_settings().llm_status
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": "down", "llm": llm})
    return JSONResponse(content={"status": "ok", "db": "ok", "llm": llm})
