"""Pydantic request/response models (API contract v1).

Validation is deliberately strict: this application handles vulnerable people's
complaints, so garbage-in must be rejected with a helpful message rather than stored.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Language = Literal["gu", "en"]

Category = Literal[
    "cyber_fraud",
    "land_revenue",
    "legal_aid",
    "consumer",
    "government_grievance",
    "women_safety",
    "labour",
    "other",
]

CATEGORIES: tuple[str, ...] = (
    "cyber_fraud",
    "land_revenue",
    "legal_aid",
    "consumer",
    "government_grievance",
    "women_safety",
    "labour",
    "other",
)

VerificationStatus = Literal["verified", "requires_human_verification", "unverified", "outdated"]
TextStatus = Literal["verified_source_text", "owner_authored_summary", "not_available"]

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=5000)]

PHONE_RE = re.compile(r"^[6-9]\d{9}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ------------------------------------------------------------------ meta/health
class Capabilities(BaseModel):
    ai_provider: str
    ai_live: bool
    ai_fallback_mode: str
    languages: list[Language]
    admin_enabled: bool
    max_upload_bytes: int
    allowed_upload_types: list[str]


class MetaResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    api_prefix: str
    capabilities: Capabilities
    corpus: dict
    disclaimers: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, str]


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, str]
    detail: dict | None = None


# ---------------------------------------------------------------- constitution
class SourceRef(BaseModel):
    source_key: str
    title: str
    publisher: str
    source_type: str
    url: str | None
    document_ref: str | None
    published_on: str | None
    retrieved_on: str | None
    last_checked_at: str | None = None


class ArticleSummary(BaseModel):
    id: int
    article_no: str
    article_label: str
    part_no: str | None
    part_title: str | None
    title_en: str | None
    title_gu: str | None
    text_status: TextStatus
    verification_status: VerificationStatus
    last_checked_at: str | None
    snippet: str | None


class ArticleDetail(ArticleSummary):
    chapter_title: str | None
    text_en: str | None
    text_gu: str | None
    citizen_explanation_en: str | None
    citizen_explanation_gu: str | None
    source_locator: str | None
    source_pages: str | None = None
    source_url: str | None
    notes: str | None
    sources: list[SourceRef]
    language_texts: list[dict] = []
    disclaimers: list[str]


class SearchResponse(BaseModel):
    query: str | None
    language: Language
    total: int
    page: int
    page_size: int
    took_ms: int
    items: list[ArticleSummary]
    notice: str | None = None


class PartSummary(BaseModel):
    part_no: str | None
    part_title: str | None
    article_count: int


class CoverageResponse(BaseModel):
    total_articles: int
    verified_text: int
    owner_summaries: int
    text_unavailable: int
    requires_human_verification: int
    parts: list[PartSummary]
    missing_standard_articles: list[str]
    expected_article_count: int
    note: str


# -------------------------------------------------------------------- AI layer
class ExplainRequest(StrictModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1500)]
    # Any language of the registry (backend/app/languages.py); answers are written in gu/en.
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")] = "gu"

    @field_validator("language")
    @classmethod
    def _registered_language(cls, value: str) -> str:
        from .languages import is_known
        if not is_known(value):
            raise ValueError("language is not in the language registry (GET /api/v1/languages)")
        return value
    category: str | None = None

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str | None) -> str | None:
        if value is not None and value not in CATEGORIES:
            raise ValueError(f"category must be one of {', '.join(CATEGORIES)}")
        return value


class Citation(BaseModel):
    article_id: int
    article_label: str
    title: str | None
    verification_status: VerificationStatus
    source_url: str | None


class GuideOut(BaseModel):
    guide_key: str
    category_en: str
    category_gu: str
    summary: str | None
    steps: list[str]
    documents: list[str]
    department_key: str | None
    verification_status: VerificationStatus
    last_checked_at: str | None


class ExplainResponse(BaseModel):
    answer: str
    language: Language
    provider: str
    model: str | None
    grounded: bool
    degraded: bool
    citations: list[Citation]
    guide: GuideOut | None
    departments: list["DepartmentOut"]
    warnings: list[str]
    disclaimers: list[str]
    request_id: str
    requested_language: str | None = None
    detected_language: dict | None = None
    language_fallback: bool = False
    language_notice: str | None = None


class TerminologyRequest(StrictModel):
    term: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    language: Language = "gu"


class TerminologyResponse(BaseModel):
    term: str
    found: bool
    explanation_en: str | None
    explanation_gu: str | None
    source_note: str
    disclaimers: list[str]


# ------------------------------------------------------------------- complaints
class ComplaintCreate(StrictModel):
    language: Language = "gu"
    category: Category
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=150)]
    description: LongText
    incident_date: date | None = None
    location: ShortText | None = None
    district: ShortText | None = None
    state: ShortText | None = None
    respondent: ShortText | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    consent: bool = Field(description="User confirms the data is theirs and may be stored")
    confirmed: bool = Field(description="User has reviewed the generated summary")
    documents: list[dict] = Field(default_factory=list, max_length=10)
    client_request_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=64)
    ] | None = Field(
        default=None,
        description=(
            "Optional idempotency key generated once by the client for this submission. "
            "Retrying with the same value returns 409 with the existing reference instead "
            "of creating a duplicate complaint."
        ),
    )

    @field_validator("incident_date")
    @classmethod
    def _not_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("incident_date cannot be in the future")
        if value and value < date(1950, 1, 26):
            raise ValueError("incident_date is implausibly early")
        return value

    @field_validator("contact_phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        cleaned = re.sub(r"[\s\-()]", "", value)
        if not PHONE_RE.match(cleaned):
            raise ValueError("contact_phone must be a 10-digit Indian mobile number")
        return cleaned

    @model_validator(mode="after")
    def _consents(self) -> "ComplaintCreate":
        if not self.consent:
            raise ValueError("consent is required to store this complaint")
        if not self.confirmed:
            raise ValueError("confirmed must be true: the user must review the summary first")
        return self


class ComplaintDocumentRef(StrictModel):
    id: int = Field(ge=1)
    token: Annotated[str, StringConstraints(min_length=10, max_length=200)]


class ComplaintCreated(BaseModel):
    reference: str
    access_token: str
    status: str
    created_at: str
    summary: str
    category: str
    next_steps: list[str]
    departments: list["DepartmentOut"]
    notice: str


class ComplaintOut(BaseModel):
    reference: str
    language: Language
    category: str
    title: str
    description: str
    summary: str
    incident_date: str | None
    location: str | None
    district: str | None
    state: str | None
    respondent: str | None
    status: str
    created_at: str
    updated_at: str
    documents: list[dict]


# -------------------------------------------------------------------- documents
class DocumentOut(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    extraction_status: str
    ocr_confidence: float | None
    created_at: str
    access_token: str | None = None


# ------------------------------------------------------------------ departments
class DepartmentOut(BaseModel):
    department_key: str
    name_en: str
    name_gu: str
    jurisdiction: str | None
    purpose_en: str | None
    purpose_gu: str | None
    portal_url: str | None
    portal_label: str | None
    helpline: str | None
    verification_status: VerificationStatus
    verified_on: str | None
    source: SourceRef | None


class DepartmentListResponse(BaseModel):
    items: list[DepartmentOut]
    count: int
    notice: str


# ---------------------------------------------------------------------- admin
class VerificationUpdate(StrictModel):
    verification_status: VerificationStatus
    last_checked_at: datetime | None = None
    checked_by: Annotated[str, StringConstraints(min_length=2, max_length=120)] | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None


class AdminStats(BaseModel):
    counts: dict[str, int]
    ai: dict
    corpus: dict
    recent_errors: int


class FeedbackCreate(StrictModel):
    target_type: Literal["ai_answer", "article", "department"]
    target_ref: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    reason: Literal["incorrect_law", "outdated", "unsafe_advice", "wrong_department", "other"]
    message: Annotated[str, StringConstraints(max_length=2000)] | None = None


ExplainResponse.model_rebuild()
ComplaintCreated.model_rebuild()


class ComplaintPreviewRequest(StrictModel):
    """Same validation as a real submission, minus the confirmation flag."""

    language: Language = "gu"
    category: Category
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=150)]
    description: LongText
    incident_date: date | None = None
    location: ShortText | None = None
    district: ShortText | None = None
    state: ShortText | None = None
    respondent: ShortText | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    consent: bool
    client_request_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=64)
    ] | None = None

    _not_future = field_validator("incident_date")(ComplaintCreate._not_future.__func__)  # type: ignore[attr-defined]
    _phone = field_validator("contact_phone")(ComplaintCreate._phone.__func__)  # type: ignore[attr-defined]

    @model_validator(mode="after")
    def _consents(self) -> "ComplaintPreviewRequest":
        if not self.consent:
            raise ValueError("consent is required to prepare a complaint")
        return self


class ComplaintPreview(BaseModel):
    summary: str
    category: str
    word_count: int
    checks: list[str]
