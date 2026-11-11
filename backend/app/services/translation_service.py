
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import TranslationEntry
from app.services.model_router import get_translation_provider
from app.services.providers.cloud_provider import (
    TranslationProviderError,
)


def find_verified_translation(
    db: Session,
    text: str,
    source_language: str,
    target_language: str,
):
    return (
        db.query(TranslationEntry)
        .filter(
            TranslationEntry.source_text == text,
            TranslationEntry.source_language.ilike(source_language),
            TranslationEntry.target_language.ilike(target_language),
            TranslationEntry.status == "verified",
        )
        .first()
    )


def generate_translation(
    text: str,
    source_language: str,
    target_language: str,
):
    provider = get_translation_provider()

    translated_text = provider.translate(
        text=text,
        source_language=source_language,
        target_language=target_language,
    )

    return translated_text, provider.provider_name


def translate_text(
    db: Session,
    text: str,
    source_language: str,
    target_language: str,
):
    text = text.strip()

    if not text:
        raise TranslationProviderError(
            "Please enter text to translate."
        )

    provider = get_translation_provider()

    # 1. Detect the real source language when Auto Detect is selected.
    if source_language.strip().casefold() in (
        "auto detect",
        "auto",
        "detect language",
    ):
        detect_function = getattr(
            provider,
            "detect_language",
            None,
        )

        if not callable(detect_function):
            raise TranslationProviderError(
                "The configured translation provider does not support "
                "automatic language detection."
            )

        source_language = detect_function(text)

    # 2. Validate the detected language.
    actual_source_language = None

    for language in settings.SUPPORTED_LANGUAGES:
        if language.casefold() == source_language.casefold():
            actual_source_language = language
            break

    if actual_source_language is None:
        raise TranslationProviderError(
            f"Unsupported detected source language: {source_language}"
        )

    source_language = actual_source_language

    # 3. Prevent translating a language into itself.
    if source_language.casefold() == target_language.casefold():
        raise TranslationProviderError(
            "The detected source language is the same as the target language."
        )

    # 4. Check the verified translation database.
    existing = find_verified_translation(
        db,
        text,
        source_language,
        target_language,
    )

    if existing:
        return {
            "original_text": text,
            "translated_text": existing.translated_text,
            "source_language": existing.source_language,
            "target_language": existing.target_language,
            "provider": "translation_database",
            "status": "verified",
            "from_database": True,
            "message": "Verified translation retrieved successfully.",
        }

    # 5. Generate a translation if no verified database entry exists.
    translated_text = provider.translate(
        text=text,
        source_language=source_language,
        target_language=target_language,
    )

    # 6. Save generated translations as pending human review.
    entry = TranslationEntry(
        source_text=text,
        translated_text=translated_text,
        source_language=source_language,
        target_language=target_language,
        provider=provider.provider_name,
        status="pending",
        translation_method="machine",
        confidence=None,
    )

    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)

    except Exception:
        db.rollback()
        raise

    return {
        "original_text": text,
        "translated_text": entry.translated_text,
        "source_language": entry.source_language,
        "target_language": entry.target_language,
        "provider": entry.provider,
        "status": entry.status,
        "from_database": False,
        "message": "Translation generated and saved for verification.",
    }
