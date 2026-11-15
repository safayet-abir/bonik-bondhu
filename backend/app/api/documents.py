"""/profiles/{pid}/documents and /extraction-drafts (API spec §4.5; P6-T03/T04)."""
from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from fastapi.responses import FileResponse

from ..core.deps import OwnedProfile, OwnerUser
from ..core.errors import AppError, not_found
from ..db import DbSession
from ..schemas.ai import DocumentOut, ExtractionDraftOut, ExtractionIn
from ..schemas.ledger import TransactionCreate, TransactionOut
from ..services import ai_service, document_service, ledger_service

router = APIRouter(prefix="/profiles/{pid}", tags=["documents"])


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=DocumentOut)
def upload_document(request: Request, profile: OwnedProfile, user: OwnerUser, db: DbSession,
                    file: Annotated[UploadFile, File()],
                    purpose: Annotated[Literal["receipt", "quotation", "loan_paper", "other"], Form()] = "receipt",
                    ) -> DocumentOut:
    limit = document_service.max_bytes()
    if int(request.headers.get("content-length") or 0) > limit + 64 * 1024:  # refuse huge bodies early
        raise AppError("FILE_TOO_LARGE", 413, "doc.err.too_large")
    raw = file.file.read(limit + 1)
    doc, duplicate = document_service.upload(db, user, profile, raw, purpose)
    return DocumentOut(id=doc.id, mime_type=doc.mime_type, size_bytes=doc.size_bytes, sha256=doc.sha256,
                       duplicate_of=duplicate)


@router.get("/documents/{did}/content")
def document_content(did: uuid.UUID, profile: OwnedProfile, db: DbSession) -> FileResponse:
    doc = document_service.get(db, profile, did)
    path = document_service.path(doc)
    if not path.is_file():  # hosts with ephemeral disks lose uploads on redeploy: 404, not a 500
        raise not_found()
    return FileResponse(path, media_type=doc.mime_type,
                        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"})


@router.post("/extraction-drafts", status_code=status.HTTP_201_CREATED, response_model=ExtractionDraftOut)
def create_draft(data: ExtractionIn, profile: OwnedProfile, user: OwnerUser, db: DbSession) -> ExtractionDraftOut:
    d, matched = ai_service.extract(db, user, profile, data.document_id, data.ai_consent)
    return ExtractionDraftOut(id=d.id, status=d.status, document_id=d.document_id, proposed=d.proposed,
                              matched_supplier_id=matched, provider=d.provider)


@router.post("/extraction-drafts/{xid}/confirm", status_code=status.HTTP_201_CREATED, response_model=TransactionOut)
def confirm_draft(xid: uuid.UUID, data: TransactionCreate, profile: OwnedProfile, user: OwnerUser,
                  db: DbSession) -> TransactionOut:
    return ledger_service.outs(db, profile, [ai_service.confirm_draft(db, user, profile, xid, data)])[0]


@router.post("/extraction-drafts/{xid}/discard", status_code=status.HTTP_204_NO_CONTENT)
def discard_draft(xid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> Response:
    ai_service.discard_draft(db, profile, xid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
