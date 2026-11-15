"""AI features with daily caps, metadata-only logging and fallbacks
(P6-T02, T04, T05, T06; AI doc §3, §5, §8, §9).

Caps (SUG-05) count this user's LLM calls since midnight Asia/Dhaka in
`ai_interactions` (status ok/error); template answers and cached results do
not count. No prompt, image or reply text is ever stored or logged (SUG-22)."""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import advisor, extraction, purpose, templates
from ..ai.grounding import grounded, has_forbidden
from ..ai.provider import AIUnavailable, Provider, image_part, json_object, providers
from ..ai.tools import HELP, Toolbox
from ..config import get_settings
from ..core.clock import DHAKA, today, utcnow
from ..core.errors import AppError, field_error, not_found
from ..models import AiInteraction, BusinessProfile, ExtractionDraft, FinancingRequestItem, Transaction, User
from ..schemas.ai import AdvisorIn
from ..schemas.ledger import TransactionCreate
from . import document_service, financing_service, ledger_service, supplier_service
from .profile_service import bump_data_version
from .snapshot_service import _scrub, name_patterns, supplier_labels

log = logging.getLogger("bonik.ai")
CAP_SETTING = {"advisor": "AI_DAILY_LIMIT_ADVISOR", "receipt_extraction": "AI_DAILY_LIMIT_EXTRACTION",
               "purpose_parse": "AI_DAILY_LIMIT_PURPOSE"}
_BANGLA = re.compile(r"[ঀ-৿]")
_LATIN = re.compile(r"[A-Za-z]")


# --------------------------------------------------------------------------- caps + logging
def used_today(db: Session, user: User, feature: str) -> int:
    start = datetime.combine(today(), time.min, DHAKA)
    return db.scalar(select(func.count()).select_from(AiInteraction).where(
        AiInteraction.user_id == user.id, AiInteraction.feature == feature, AiInteraction.created_at >= start,
        AiInteraction.status.in_(("ok", "error")))) or 0


def record(db: Session, user: User, profile: BusinessProfile, feature: str, status: str, p: Provider | None = None,
           *, input_tokens: int | None = None, output_tokens: int | None = None, latency_ms: int | None = None,
           tools: list[str] | None = None, grounding: str = "not_applicable") -> None:
    db.add(AiInteraction(user_id=user.id, profile_id=profile.id, feature=feature, status=status,
                         provider=p.name if p else "none", model=p.model if p else None, input_tokens=input_tokens,
                         output_tokens=output_tokens, latency_ms=latency_ms, tools_called=tools or [],
                         grounding_check=grounding))
    db.flush()
    log.info("ai call", extra={"feature": feature, "status": status, "provider": p.name if p else "none",
                               "grounding_check": grounding, "latency_ms": latency_ms})


def _limit_check(db: Session, user: User, profile: BusinessProfile, feature: str, extra: dict | None = None) -> None:
    if used_today(db, user, feature) >= getattr(get_settings(), CAP_SETTING[feature]):
        record(db, user, profile, feature, "limit")
        raise AppError("AI_DAILY_LIMIT", 429, "ai.err.daily_limit", extra=extra, commit=True)


def _unavailable(key: str = "ai.err.unavailable", extra: dict | None = None) -> AppError:
    return AppError("AI_UNAVAILABLE", 503, key, extra=extra, commit=True)


# --------------------------------------------------------------------------- receipt -> draft
def extract(db: Session, user: User, profile: BusinessProfile, document_id: uuid.UUID,
            ai_consent: bool) -> tuple[ExtractionDraft, uuid.UUID | None]:
    if not ai_consent:  # FR-EXT-05: the owner agreed to send this photo to the AI provider
        raise field_error("ai_consent", "ai.err.consent_required")
    doc = document_service.get(db, profile, document_id)
    plist = providers("receipt_extraction")
    if not plist:
        record(db, user, profile, "receipt_extraction", "fallback")
        raise _unavailable()
    _limit_check(db, user, profile, "receipt_extraction")
    p = plist[0]
    messages = [{"role": "user", "content": [{"type": "text", "text": extraction.PROMPT},
                                             image_part(document_service.path(doc).read_bytes(), doc.mime_type)]}]
    try:
        reply = p.chat(messages, max_tokens=800)
    except AIUnavailable:
        record(db, user, profile, "receipt_extraction", "error", p)
        raise _unavailable() from None
    draft = ExtractionDraft(profile_id=profile.id, document_id=doc.id, provider=p.name, model=p.model)
    try:
        draft.proposed = extraction.proposed(json_object(reply.text), today())
    except ValueError:
        draft.status, draft.proposed, draft.resolved_at = "failed", {}, utcnow()
        db.add(draft)
        record(db, user, profile, "receipt_extraction", "error", p, input_tokens=reply.input_tokens,
               output_tokens=reply.output_tokens, latency_ms=reply.latency_ms)
        db.flush()
        raise AppError("EXTRACTION_FAILED", 422, "ai.err.extraction_failed", extra={"draft_id": str(draft.id)},
                       commit=True) from None
    db.add(draft)
    record(db, user, profile, "receipt_extraction", "ok", p, input_tokens=reply.input_tokens,
           output_tokens=reply.output_tokens, latency_ms=reply.latency_ms)
    db.flush()
    db.refresh(draft)
    name = (draft.proposed.get("supplier_name") or {}).get("value")
    matched = next((s.id for s in supplier_service.list_suppliers(db, profile, include_inactive=False)
                    if name and s.display_name.strip().casefold() == name.strip().casefold()), None)
    return draft, matched


def _draft(db: Session, profile: BusinessProfile, xid: uuid.UUID) -> ExtractionDraft:
    d = db.scalar(select(ExtractionDraft).where(ExtractionDraft.profile_id == profile.id, ExtractionDraft.id == xid))
    if d is None:
        raise not_found()
    if d.status != "pending":
        raise AppError("DRAFT_ALREADY_RESOLVED", 409, "ai.err.draft_resolved")
    return d


def confirm_draft(db: Session, user: User, profile: BusinessProfile, xid: uuid.UUID,
                  data: TransactionCreate) -> Transaction:
    """FR-EXT-03: the owner's edited values become the entry, with the photo as evidence."""
    d = _draft(db, profile, xid)
    txn, _ = ledger_service.create(db, user, profile, data, entry_method="photo_assisted", document_id=d.document_id)
    d.status, d.confirmed_transaction_id, d.resolved_at = "confirmed", txn.id, utcnow()
    db.flush()
    return txn


def discard_draft(db: Session, profile: BusinessProfile, xid: uuid.UUID) -> None:
    d = _draft(db, profile, xid)
    d.status, d.resolved_at = "discarded", utcnow()
    document_service.drop_file(db, profile, d.document_id)
    db.flush()


# --------------------------------------------------------------------------- purpose -> items
# shortcut: in-process cache of (request, sha256(purpose text)); after a restart the same text costs one more AI call
_PARSED: set[tuple[uuid.UUID, str]] = set()


def parse_purpose(db: Session, user: User, profile: BusinessProfile, rid: uuid.UUID) -> list[FinancingRequestItem]:
    r = financing_service.get(db, profile, rid)
    key = (r.id, hashlib.sha256(r.purpose_text.encode("utf-8")).hexdigest())
    pending = [i for i in financing_service.list_items(db, profile, r) if i.ai_proposed and not i.confirmed]
    if key in _PARSED and pending:
        return pending  # same text, suggestions still there: no new AI call
    plist = providers("purpose_parse")
    if not plist:
        record(db, user, profile, "purpose_parse", "fallback")
        raise _unavailable()
    _limit_check(db, user, profile, "purpose_parse")
    _, _, names = supplier_labels(db, profile, today())
    text = _scrub(r.purpose_text, name_patterns(names))  # supplier names never go to the LLM
    messages = [{"role": "system", "content": purpose.PROMPT}, {"role": "user", "content": text}]
    for p in plist:
        try:
            reply = p.chat(messages, max_tokens=800)
            break
        except AIUnavailable:
            record(db, user, profile, "purpose_parse", "error", p)
    else:
        raise _unavailable()
    try:
        rows = purpose.items(json_object(reply.text))
    except ValueError:
        record(db, user, profile, "purpose_parse", "error", p, input_tokens=reply.input_tokens,
               output_tokens=reply.output_tokens, latency_ms=reply.latency_ms)
        raise _unavailable("ai.err.parse_failed") from None
    record(db, user, profile, "purpose_parse", "ok", p, input_tokens=reply.input_tokens,
           output_tokens=reply.output_tokens, latency_ms=reply.latency_ms)
    for old in pending:  # new suggestions replace the previous unconfirmed ones
        db.delete(old)
    items = [FinancingRequestItem(profile_id=profile.id, financing_request_id=r.id, item_name=row["item_name"],
                                  quantity=row["quantity"], unit=row["unit"], unit_price=0,
                                  price_source_type="owner_estimate", ai_proposed=True, confirmed=False)
             for row in rows]
    db.add_all(items)
    r.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    for i in items:
        db.refresh(i)
    _PARSED.add(key)
    return items


# --------------------------------------------------------------------------- advisor
def language(message: str, user: User) -> str:
    if _BANGLA.search(message):
        return "bn"
    if _LATIN.search(message):
        return "en"
    return user.preferred_language or "bn"


def help_payload(tb: Toolbox, lang: str) -> dict:
    """Help menu for the no-LLM path (FR-ADV-07): static topics + answers computed from this profile."""
    return {"items": HELP,
            "quick": [{"key": k, "title": templates.TITLES[k][0 if lang == "bn" else 1],
                       "answer": templates.answer(k, tb, lang)} for k in templates.QUICK]}


def advise(db: Session, user: User, profile: BusinessProfile, data: AdvisorIn) -> dict:
    lang = language(data.message, user)
    tb = Toolbox(db, profile, lang)
    plist = providers("advisor")
    if not plist:
        record(db, user, profile, "advisor", "fallback")
        raise _unavailable(extra={"help_topics": help_payload(tb, lang)})
    _limit_check(db, user, profile, "advisor", extra={"help_topics": help_payload(tb, lang)})
    system = advisor.PROMPT.format(activity="shop" if tb.shop else "crop farm",
                                   language="Bangla" if lang == "bn" else "English", today=tb.today.isoformat())
    history = [t.model_dump() for t in data.history][-12:]
    for p in plist:
        try:
            ans = advisor.run(p, system, history, data.message, tb.specs(), tb.run)
            break
        except AIUnavailable:
            record(db, user, profile, "advisor", "error", p)
    else:
        raise _unavailable(extra={"help_topics": help_payload(tb, lang)})
    sources = [*ans.tool_outputs, data.message, tb.today.isoformat()]
    ok = bool(ans.text) and grounded(ans.text, sources) and not has_forbidden(ans.text)
    record(db, user, profile, "advisor", "ok", p, input_tokens=ans.input_tokens, output_tokens=ans.output_tokens,
           latency_ms=ans.latency_ms, tools=ans.tools_used, grounding="passed" if ok else "failed")
    if ok:
        return {"reply": ans.text, "language": lang, "tools_used": ans.tools_used, "grounded": True, "mode": "llm"}
    # SUG-23: discard the reply; answer from the tool the model used (numbers grounded by construction)
    key = next((templates.TOOL_FOR[t] for t in ans.tools_used if t in templates.TOOL_FOR), None)
    if has_forbidden(ans.text):
        reply = templates.LENDER_DECIDES[lang]
    elif key:
        reply = templates.answer(key, tb, lang)
    else:
        reply = ("এই প্রশ্নের যাচাই করা উত্তর দিতে পারিনি। নিচের বোতামগুলো দেখুন।" if lang == "bn"
                 else "I could not give a checked answer to this. Please use the buttons below.")
    return {"reply": reply, "language": lang, "tools_used": ans.tools_used, "grounded": False, "mode": "template"}
