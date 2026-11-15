"""Receipt photo uploads (P6-T03; FR-EXT-01; SEC-17; SUG-18). JPEG/PNG only,
checked by magic bytes (not the file name), ≤ MAX_UPLOAD_MB, decoded and
re-encoded with Pillow (EXIF and all other metadata dropped, longest side
≤ 1600 px), stored under a random name in a private folder and served only
to the owning profile with no-store."""
from __future__ import annotations

import hashlib
import io
import secrets
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import BACKEND_DIR, get_settings
from ..core.errors import AppError, not_found
from ..models import BusinessProfile, Document, User

MAX_SIDE = 1600
MAX_PIXELS = 40_000_000  # refuse decompression bombs before decoding
MAGIC = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))
DB_MAX_BYTES = 5_242_880  # documents.size_bytes CHECK


def max_bytes() -> int:
    return min(get_settings().MAX_UPLOAD_MB * 1024 * 1024, DB_MAX_BYTES)


def _folder() -> Path:
    p = Path(get_settings().UPLOAD_DIR)
    p = p if p.is_absolute() else BACKEND_DIR / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reencode(raw: bytes, mime: str) -> bytes:
    unsupported = AppError("UNSUPPORTED_FILE_TYPE", 415, "doc.err.type")
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise unsupported
            im = ImageOps.exif_transpose(im)  # keep the photo upright; the EXIF itself is not saved
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            out = io.BytesIO()
            if mime == "image/jpeg":
                im.convert("RGB").save(out, "JPEG", quality=85)
            else:
                im.save(out, "PNG", optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise unsupported from None


def upload(db: Session, user: User, profile: BusinessProfile, raw: bytes,
           purpose: str = "receipt") -> tuple[Document, uuid.UUID | None]:
    if len(raw) > max_bytes():
        raise AppError("FILE_TOO_LARGE", 413, "doc.err.too_large")
    mime = next((m for sig, m in MAGIC if raw.startswith(sig)), None)
    if mime is None:
        raise AppError("UNSUPPORTED_FILE_TYPE", 415, "doc.err.type")
    data = _reencode(raw, mime)
    if len(data) > DB_MAX_BYTES:
        raise AppError("FILE_TOO_LARGE", 413, "doc.err.too_large")
    digest = hashlib.sha256(raw).hexdigest()  # of the original photo: the same photo twice = duplicate evidence
    duplicate = db.scalar(select(Document.id).where(Document.profile_id == profile.id, Document.sha256 == digest)
                          .order_by(Document.created_at).limit(1))
    key = secrets.token_hex(16) + (".jpg" if mime == "image/jpeg" else ".png")
    # shortcut: if the request later fails, the file stays on disk unreferenced; add a cleanup job if uploads grow
    try:
        (_folder() / key).write_bytes(data)
    except OSError:  # FS-03: storage full / not writable -> 503; manual entry still works
        raise AppError("SERVICE_UNAVAILABLE", 503, "doc.err.storage") from None
    doc = Document(profile_id=profile.id, uploaded_by=user.id, storage_key=key, mime_type=mime,
                   size_bytes=len(data), sha256=digest, purpose=purpose)
    db.add(doc)
    db.flush()
    db.refresh(doc)
    return doc, duplicate


def get(db: Session, profile: BusinessProfile, did: uuid.UUID) -> Document:
    doc = db.scalar(select(Document).where(Document.profile_id == profile.id, Document.id == did))
    if doc is None:
        raise not_found()
    return doc


def path(doc: Document) -> Path:
    return _folder() / doc.storage_key


def drop_file(db: Session, profile: BusinessProfile, did: uuid.UUID) -> None:
    """SUG-52: the photo is only needed while the owner checks the entry. Once the entry is saved
    (or the draft discarded) the image is deleted; the row keeps sha256 + upload time, so the
    duplicate-photo warning still works and no receipt image (third-party names, phones) is kept."""
    path(get(db, profile, did)).unlink(missing_ok=True)
