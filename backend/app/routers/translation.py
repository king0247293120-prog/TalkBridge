
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.database.models import (
    TranslationEntry,
    TranslationReport,
)
from app.database.schemas import (
    TranslationRequest,
    TranslationResponse,
    TranslationReviewRequest,
    TranslationReportRequest,
)

from app.services.translation_service import translate_text

from app.services.providers.cloud_provider import (
    TranslationProviderError,
    TranslationProviderUnavailable,
)

from app.services.providers.runpod_provider import (
    RunpodProviderError,
    RunpodProviderUnavailable,
)


router = APIRouter(
    prefix="/translation",
    tags=["Translation Intelligence"],
)


# ==================================================
# LANGUAGE VALIDATION
# ==================================================


def normalize_language(language: str, allow_auto: bool = False) -> str:
    language = language.strip()

    if allow_auto and language.casefold() in (
        "auto detect",
        "auto",
        "detect language",
    ):
        return "Auto Detect"

    for supported_language in settings.SUPPORTED_LANGUAGES:
        if language.casefold() == supported_language.casefold():
            return supported_language

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported language: {language}",
    )


# ==================================================
# 1. TRANSLATE TEXT
# ==================================================

@router.post("/translate", response_model=TranslationResponse)
def translate(
    request: TranslationRequest,
    db: Session = Depends(get_db),
):
    source_language = normalize_language(
    request.source_language,
    allow_auto=True,
)

    target_language = normalize_language(
        request.target_language
    )

    if source_language.casefold() == target_language.casefold():
        raise HTTPException(
            status_code=400,
            detail="Source and target languages must be different.",
        )

    try:
        result = translate_text(
            db=db,
            text=request.text,
            source_language=source_language,
            target_language=target_language,
        )

        return result

    except (
        TranslationProviderUnavailable,
        RunpodProviderUnavailable,
    ) as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except (
        TranslationProviderError,
        RunpodProviderError,
    ) as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="An unexpected translation error occurred.",
        )


# ==================================================
# 2. GET PENDING TRANSLATIONS
# ==================================================

@router.get("/pending")
def get_pending_translations(
    db: Session = Depends(get_db),
):
    try:
        translations = (
            db.query(TranslationEntry)
            .filter(
                TranslationEntry.status == "pending"
            )
            .order_by(
                TranslationEntry.created_at.desc()
            )
            .all()
        )

        return {
            "total": len(translations),
            "status": "success",
            "translations": [
                {
                    "id": item.id,
                    "source_text": item.source_text,
                    "translated_text": item.translated_text,
                    "source_language": item.source_language,
                    "target_language": item.target_language,
                    "provider": item.provider,
                    "translation_method": item.translation_method,
                    "confidence": item.confidence,
                    "status": item.status,
                    "created_at": item.created_at,
                }
                for item in translations
            ],
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve pending translations.",
        )


# ==================================================
# 3. REVIEW, APPROVE OR REJECT TRANSLATIONS
# ==================================================

@router.put("/{translation_id}/review")
def review_translation(
    translation_id: int,
    review: TranslationReviewRequest,
    db: Session = Depends(get_db),
):
    translation = (
        db.query(TranslationEntry)
        .filter(
            TranslationEntry.id == translation_id
        )
        .first()
    )

    if translation is None:
        raise HTTPException(
            status_code=404,
            detail="Translation not found.",
        )

    if translation.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending translations can be reviewed.",
        )

    if review.translated_text is not None:
        corrected_text = review.translated_text.strip()

        if not corrected_text:
            raise HTTPException(
                status_code=400,
                detail="Translated text cannot be empty.",
            )

        translation.translated_text = corrected_text

    if review.source_language is not None:
        translation.source_language = normalize_language(
            review.source_language
        )

    if review.target_language is not None:
        translation.target_language = normalize_language(
            review.target_language
        )

    if review.decision == "approve":

        translation.source_language = normalize_language(
            translation.source_language
        )

        translation.target_language = normalize_language(
            translation.target_language
        )

        if (
            translation.source_language.casefold()
            == translation.target_language.casefold()
        ):
            raise HTTPException(
                status_code=400,
                detail="Source and target languages must be different.",
            )

        if not translation.translated_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Cannot approve an empty translation.",
            )

        translation.status = "verified"
        translation.translation_method = "human"

    elif review.decision == "reject":
        translation.status = "rejected"

    translation.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(translation)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to save translation review.",
        )

    return {
        "id": translation.id,
        "source_text": translation.source_text,
        "translated_text": translation.translated_text,
        "source_language": translation.source_language,
        "target_language": translation.target_language,
        "provider": translation.provider,
        "translation_method": translation.translation_method,
        "status": translation.status,
        "decision": review.decision,
        "message": (
            "Translation approved and verified."
            if review.decision == "approve"
            else "Translation rejected successfully."
        ),
    }


# ==================================================
# 4. REPORT AN INCORRECT TRANSLATION
# ==================================================

@router.post("/{translation_id}/report")
def report_translation(
    translation_id: int,
    report: TranslationReportRequest,
    db: Session = Depends(get_db),
):
    translation = (
        db.query(TranslationEntry)
        .filter(
            TranslationEntry.id == translation_id
        )
        .first()
    )

    if translation is None:
        raise HTTPException(
            status_code=404,
            detail="Translation not found.",
        )

    reason = report.reason.strip()

    if not reason:
        raise HTTPException(
            status_code=400,
            detail="Please provide a reason for the report.",
        )

    suggested_correction = None

    if report.suggested_correction is not None:
        suggested_correction = (
            report.suggested_correction.strip()
        )

        if not suggested_correction:
            suggested_correction = None

    new_report = TranslationReport(
        translation_id=translation.id,
        reason=reason,
        suggested_correction=suggested_correction,
        status="pending",
    )

    try:
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

    except Exception as error:
        db.rollback()

        print(
            "TRANSLATION REPORT DATABASE ERROR:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to submit translation report.",
        )

    return {
        "report_id": new_report.id,
        "translation_id": translation.id,
        "reason": new_report.reason,
        "suggested_correction": new_report.suggested_correction,
        "status": new_report.status,
        "message": "Translation report submitted successfully.",
    }


# ==================================================
# 5. GET PENDING TRANSLATION REPORTS
# ==================================================

@router.get("/reports/pending")
def get_pending_reports(
    db: Session = Depends(get_db),
):
    try:
        reports = (
            db.query(TranslationReport)
            .filter(
                TranslationReport.status == "pending"
            )
            .order_by(
                TranslationReport.created_at.desc()
            )
            .all()
        )

        return {
            "total": len(reports),
            "status": "success",
            "reports": [
                {
                    "report_id": report.id,
                    "translation_id": report.translation_id,
                    "source_text": report.translation.source_text,
                    "translated_text": report.translation.translated_text,
                    "source_language": report.translation.source_language,
                    "target_language": report.translation.target_language,
                    "reason": report.reason,
                    "suggested_correction": report.suggested_correction,
                    "report_status": report.status,
                    "created_at": report.created_at,
                }
                for report in reports
            ],
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve translation reports.",
        )
