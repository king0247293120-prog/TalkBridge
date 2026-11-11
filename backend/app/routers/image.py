from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.translation_service import translate_text

from app.services.providers.cloud_provider import (
    TranslationProviderError,
    TranslationProviderUnavailable,
)

from app.services.providers.runpod_provider import (
    RunpodProviderError,
    RunpodProviderUnavailable,
)
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.services.image_service import (
    analyze_image,
    extract_image_text,
    ImageServiceError,
    ImageServiceUnavailable,
)


router = APIRouter(
    prefix="/image",
    tags=["Image Intelligence"],
)


def detect_image_type(data: bytes) -> str | None:

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ):
        return "image/webp"

    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"

    return None
def normalize_language(language: str) -> str:
    language = language.strip()

    for supported_language in settings.SUPPORTED_LANGUAGES:
        if language.casefold() == supported_language.casefold():
            return supported_language

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported language: {language}",
    )

@router.post("/analyze")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    question: str = Form(
        "Describe this image in detail."
    ),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select an image.",
        )

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format.",
        )

    image_bytes = await file.read(
        settings.IMAGE_MAX_UPLOAD_SIZE + 1
    )

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(image_bytes) > settings.IMAGE_MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 10 MB upload limit.",
        )

    actual_type = detect_image_type(image_bytes)

    if actual_type != file.content_type:
        raise HTTPException(
            status_code=415,
            detail="The file content does not match its image type.",
        )

    question = question.strip()

    if not question:
        question = "Describe this image in detail."

    try:
        result = await analyze_image(
            image_bytes=image_bytes,
            mime_type=actual_type,
            question=question,
        )

        return {
            "filename": file.filename,
            "image_type": actual_type,
            "model": settings.OPENAI_VISION_MODEL,
            "analysis": result,
            "status": "success",
        }

    except ImageServiceUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except ImageServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

@router.post("/extract-text")
async def extract_text_from_image(
    file: UploadFile = File(...),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select an image.",
        )

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format.",
        )

    image_bytes = await file.read(
        settings.IMAGE_MAX_UPLOAD_SIZE + 1
    )

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(image_bytes) > settings.IMAGE_MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 10 MB upload limit.",
        )

    actual_type = detect_image_type(image_bytes)

    if actual_type != file.content_type:
        raise HTTPException(
            status_code=415,
            detail="The file content does not match its image type.",
        )

    try:
        extracted_text = await extract_image_text(
            image_bytes=image_bytes,
            mime_type=actual_type,
        )

        return {
            "filename": file.filename,
            "image_type": actual_type,
            "model": settings.OPENAI_VISION_MODEL,
            "extracted_text": extracted_text,
            "status": "success",
        }

    except ImageServiceUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except ImageServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

@router.post("/translate")
async def translate_image_text(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select an image.",
        )

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format.",
        )

    source_language = normalize_language(source_language)
    target_language = normalize_language(target_language)

    if source_language.casefold() == target_language.casefold():
        raise HTTPException(
            status_code=400,
            detail="Source and target languages must be different.",
        )

    image_bytes = await file.read(
        settings.IMAGE_MAX_UPLOAD_SIZE + 1
    )

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(image_bytes) > settings.IMAGE_MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 10 MB upload limit.",
        )

    actual_type = detect_image_type(image_bytes)

    if actual_type != file.content_type:
        raise HTTPException(
            status_code=415,
            detail="The file content does not match its image type.",
        )

    try:
        # First: extract text from the image.
        extracted_text = await extract_image_text(
            image_bytes=image_bytes,
            mime_type=actual_type,
        )

        # Second: translate the extracted text using
        # TalkBridge's existing database-first translation service.
        translation_result = translate_text(
            db=db,
            text=extracted_text,
            source_language=source_language,
            target_language=target_language,
        )

        return {
            "filename": file.filename,
            "source_language": source_language,
            "target_language": target_language,
            "extracted_text": extracted_text,
            "translated_text": translation_result["translated_text"],
            "translation_provider": translation_result["provider"],
            "translation_status": translation_result["status"],
            "translation_from_database": translation_result["from_database"],
            "status": "success",
        }

    except ImageServiceUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except ImageServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

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
            detail="An unexpected image translation error occurred.",
        )
