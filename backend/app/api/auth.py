"""/auth/* (API spec §4.2). There is deliberately no password-reset endpoint
(FR-AUTH-09, DEC-21): resets go through the admin CLI."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from ..config import get_settings
from ..core.deps import SESSION_COOKIE, CurrentAuth
from ..db import DbSession
from ..schemas.auth import LoginIn, MeOut, MePatch, RegisterIn, UserOut
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(data: RegisterIn, request: Request, db: DbSession) -> UserOut:
    # No auto-login: the client calls /auth/login next (API spec §4.2).
    return auth_service.user_out(auth_service.register(db, data, request))


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, request: Request, response: Response, db: DbSession) -> UserOut:
    result = auth_service.login(db, data, request)
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        max_age=result.max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=get_settings().is_production,
        path="/",
    )
    return auth_service.user_out(result.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(ctx: CurrentAuth, request: Request, response: Response, db: DbSession) -> Response:
    auth_service.logout(db, ctx.session, ctx.user, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=get_settings().is_production)
    return response


@router.get("/me", response_model=MeOut)
def me(ctx: CurrentAuth, db: DbSession) -> MeOut:
    return auth_service.me_out(db, ctx.user)


@router.patch("/me", response_model=MeOut)
def patch_me(patch: MePatch, ctx: CurrentAuth, db: DbSession) -> MeOut:
    auth_service.update_me(ctx.user, patch)
    return auth_service.me_out(db, ctx.user)
