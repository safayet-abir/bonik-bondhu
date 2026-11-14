"""App factory: `uvicorn app.main:create_app --factory` (TRD §4)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from .api import auth, health, lender, profiles, transactions
from .config import get_settings
from .core.errors import install_error_handlers
from .core.logging import configure_logging
from .core.middleware import CSRF_HEADER, install_middleware

API_V1 = "/api/v1"


class SPAStaticFiles(StaticFiles):
    """Serves the built React app; unknown non-API paths fall back to
    index.html so client-side routes survive a reload."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Bonik Bondhu API",
        version="0.1.0",
        openapi_url=f"{API_V1}/openapi.json",
        docs_url=f"{API_V1}/docs" if not settings.is_production else None,
        redoc_url=None,
    )
    install_error_handlers(app)
    install_middleware(app, settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", CSRF_HEADER],
    )

    for router in (health.router, auth.router, profiles.router, transactions.router, lender.router):
        app.include_router(router, prefix=API_V1)

    dist = settings.frontend_dist_path
    if (dist / "index.html").is_file():
        app.mount("/", SPAStaticFiles(directory=dist, html=True), name="spa")

    return app
