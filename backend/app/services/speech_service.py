from io import BytesIO

from openai import (
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    APIStatusError,
)

from app.core.config import settings


class SpeechServiceError(Exception):
    pass


class SpeechServiceUnavailable(Exception):
    pass


def get_speech_client():
    if not settings.OPENAI_API_KEY:
        raise SpeechServiceUnavailable(
            "Speech service is not configured."
        )

    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT,
    )


async def transcribe_audio(
    filename: str,
    audio_bytes: bytes,
    content_type: str,
    language: str | None = None,
) -> str:

    client = get_speech_client()

    try:
        options = {
            "model": settings.OPENAI_TRANSCRIPTION_MODEL,
            "file": (
                filename,
                BytesIO(audio_bytes),
                content_type,
            ),
        }

        if language:
            options["language"] = language

        response = await client.audio.transcriptions.create(
            **options
        )

        return response.text.strip()

    except AuthenticationError as exc:
        raise SpeechServiceUnavailable(
            "Speech authentication failed."
        ) from exc

    except RateLimitError as exc:
        raise SpeechServiceUnavailable(
            "Speech usage limit reached."
        ) from exc

    except (APIConnectionError, APITimeoutError) as exc:
        raise SpeechServiceUnavailable(
            "Could not connect to the speech service."
        ) from exc

    except BadRequestError as exc:
        raise SpeechServiceError(
            "The audio file could not be processed."
        ) from exc

    except APIStatusError as exc:
        raise SpeechServiceUnavailable(
            "The speech provider returned an error."
        ) from exc


async def generate_speech(
    text: str,
    voice: str | None = None,
) -> bytes:

    client = get_speech_client()

    selected_voice = voice or settings.OPENAI_TTS_VOICE

    try:
        response = await client.audio.speech.create(
            model=settings.OPENAI_TTS_MODEL,
            voice=selected_voice,
            input=text,
            response_format="mp3",
        )

        return response.content

    except AuthenticationError as exc:
        raise SpeechServiceUnavailable(
            "Speech authentication failed."
        ) from exc

    except RateLimitError as exc:
        raise SpeechServiceUnavailable(
            "Speech usage limit reached."
        ) from exc

    except (APIConnectionError, APITimeoutError) as exc:
        raise SpeechServiceUnavailable(
            "Could not connect to the speech service."
        ) from exc

    except BadRequestError as exc:
        raise SpeechServiceError(
            "The text-to-speech request was rejected."
        ) from exc

    except APIStatusError as exc:
        raise SpeechServiceUnavailable(
            "The speech provider returned an error."
        ) from exc