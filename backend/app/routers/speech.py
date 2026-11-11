
import base64
from io import BytesIO

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.database.database import get_db
from app.services.speech_service import (
    transcribe_audio,
    generate_speech,
    SpeechServiceError,
    SpeechServiceUnavailable,
)
from app.services.translation_service import translate_text


router = APIRouter(
    prefix="/speech",
    tags=["Speech Intelligence"],
)


ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "video/mp4",
}

ALLOWED_VOICES = {
    "alloy", "ash", "ballad", "coral", "echo",
    "fable", "onyx", "nova", "sage", "shimmer",
}


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str = "alloy"


def handle_speech_error(exc):
    if isinstance(exc, SpeechServiceUnavailable):
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    if isinstance(exc, SpeechServiceError):
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=500,
        detail="An unexpected speech processing error occurred.",
    ) from exc


def normalize_language(language: str) -> str:
    for supported in settings.SUPPORTED_LANGUAGES:
        if supported.lower() == language.strip().lower():
            return supported

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported language: {language}",
    )


async def read_audio(file: UploadFile):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="An audio filename is required.",
        )

    media_type = (
        (file.content_type or "")
        .split(";")[0]
        .strip()
        .lower()
    )

    if media_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format.",
        )

    audio_bytes = await file.read(
        settings.SPEECH_MAX_UPLOAD_SIZE + 1
    )

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="The audio file is empty.",
        )

    if len(audio_bytes) > settings.SPEECH_MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file exceeds the 25 MB upload limit.",
        )

    return audio_bytes, media_type


async def process_translation(
    original_text: str,
    source_language: str,
    target_language: str,
):
    db_generator = get_db()
    db = next(db_generator)

    try:
        return translate_text(
            db=db,
            text=original_text,
            source_language=source_language,
            target_language=target_language,
        )
    finally:
        db_generator.close()


async def process_voice_turn(
    file: UploadFile,
    source_language: str,
    target_language: str,
    voice: str,
):
    audio_bytes, media_type = await read_audio(file)

    source_language = normalize_language(source_language)
    target_language = normalize_language(target_language)

    if source_language == target_language:
        raise HTTPException(
            status_code=400,
            detail="Choose two different languages.",
        )

    selected_voice = voice.lower()

    if selected_voice not in ALLOWED_VOICES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported voice selection.",
        )

    try:
        original_text = await transcribe_audio(
            filename=file.filename,
            audio_bytes=audio_bytes,
            content_type=media_type,
        )

        if not original_text:
            raise HTTPException(
                status_code=422,
                detail="No speech was detected in the audio.",
            )

        translation = await process_translation(
            original_text,
            source_language,
            target_language,
        )

        translated_text = translation["translated_text"]

        if not translated_text.strip():
            raise HTTPException(
                status_code=502,
                detail="Translation returned empty text.",
            )

        audio = await generate_speech(
            text=translated_text,
            voice=selected_voice,
        )

        return {
            "original_text": original_text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "translation_provider": translation["provider"],
            "translation_status": translation["status"],
            "translation_from_database": translation["from_database"],
            "voice": selected_voice,
            "audio_format": "mp3",
            "audio_base64": base64.b64encode(audio).decode("utf-8"),
        }

    except HTTPException:
        raise

    except (SpeechServiceError, SpeechServiceUnavailable) as exc:
        handle_speech_error(exc)


@router.get("/voices")
async def get_speech_voices():
    return {
        "status": "success",
        "voices": sorted(ALLOWED_VOICES),
        "default_voice": settings.OPENAI_TTS_VOICE,
    }


@router.post("/transcribe")
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = Form(""),
):
    audio_bytes, media_type = await read_audio(file)

    if language.strip():
        normalize_language(language)

    try:
        text = await transcribe_audio(
            filename=file.filename,
            audio_bytes=audio_bytes,
            content_type=media_type,
            language=language.strip() or None,
        )

        return {
            "status": "success",
            "department": "Speech Intelligence",
            "operation": "speech_to_text",
            "filename": file.filename,
            "transcribed_text": text,
            "model": settings.OPENAI_TRANSCRIPTION_MODEL,
        }

    except (SpeechServiceError, SpeechServiceUnavailable) as exc:
        handle_speech_error(exc)


@router.post("/speak")
async def text_to_speech(request: SpeechRequest):
    voice = request.voice.lower()

    if voice not in ALLOWED_VOICES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported voice selection.",
        )

    try:
        audio = await generate_speech(
            text=request.text,
            voice=voice,
        )

        return StreamingResponse(
            BytesIO(audio),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition":
                    'attachment; filename="talkbridge_speech.mp3"'
            },
        )

    except (SpeechServiceError, SpeechServiceUnavailable) as exc:
        handle_speech_error(exc)


@router.post("/translate")
async def voice_translation(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    voice: str = Form("alloy"),
):
    result = await process_voice_turn(
        file,
        source_language,
        target_language,
        voice,
    )

    return {
        "status": "success",
        "department": "Speech Intelligence",
        "operation": "voice_translation",
        "filename": file.filename,
        "transcription_model": settings.OPENAI_TRANSCRIPTION_MODEL,
        "speech_model": settings.OPENAI_TTS_MODEL,
        **result,
    }


@router.post("/conversation-turn")
async def conversation_turn(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    voice: str = Form("alloy"),
):
    result = await process_voice_turn(
        file,
        source_language,
        target_language,
        voice,
    )

    return {
        "status": "success",
        "department": "Speech Intelligence",
        "operation": "conversation_turn",
        "filename": file.filename,
        "transcription_model": settings.OPENAI_TRANSCRIPTION_MODEL,
        "speech_model": settings.OPENAI_TTS_MODEL,
        **result,
    }
