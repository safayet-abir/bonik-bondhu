from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .common import InModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    mime_type: str
    size_bytes: int
    sha256: str
    duplicate_of: uuid.UUID | None  # same photo uploaded before (S1 F1 duplicated evidence)


class ExtractionIn(InModel):
    document_id: uuid.UUID
    ai_consent: bool = False


class ExtractionDraftOut(BaseModel):
    id: uuid.UUID
    status: str
    document_id: uuid.UUID
    proposed: dict
    matched_supplier_id: uuid.UUID | None
    provider: str
    label_key: str = "ai.suggestion_confirm"


class Turn(InModel):
    role: Literal["user", "assistant"]
    text: Annotated[str, Field(max_length=2000)]


class AdvisorIn(InModel):
    message: Annotated[str, Field(min_length=1, max_length=500)]
    history: Annotated[list[Turn], Field(max_length=12)] = []  # ≤ 6 turns = 12 messages, held by the client


class AdvisorOut(BaseModel):
    reply: str
    language: str
    tools_used: list[str]
    grounded: bool
    mode: Literal["llm", "template"]
