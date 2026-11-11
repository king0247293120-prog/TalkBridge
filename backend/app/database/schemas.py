
from typing import Literal

from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Text to translate",
    )

    source_language: str = Field(
        ...,
        min_length=1,
    )

    target_language: str = Field(
        ...,
        min_length=1,
    )


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    status: str
    from_database: bool
    message: str


class TranslationReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]

    translated_text: str | None = None

    source_language: str | None = None

    target_language: str | None = None

class TranslationReportRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )

    suggested_correction: str | None = Field(
        default=None,
        max_length=10000,
    )
