
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME = "TalkBridge"
    VERSION = "2.0.0"
    DESCRIPTION = (
        "An intelligent language, translation and communication platform."
    )

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///./talkbridge.db",
    )

    # File uploads
    UPLOAD_DIR = "uploads"
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024

    # Translation configuration
    TRANSLATION_PROVIDER = os.getenv(
        "TRANSLATION_PROVIDER",
        "openai",
    )

    TRANSLATION_MODEL = os.getenv(
        "TRANSLATION_MODEL",
        "gpt-6-luna",
    )

    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-luna",
    )

    OPENAI_TIMEOUT = int(
        os.getenv("OPENAI_TIMEOUT", "90")
    )

    # Image Intelligence configuration
    OPENAI_VISION_MODEL = os.getenv(
        "OPENAI_VISION_MODEL",
        "gpt-4.1",
    )

    IMAGE_MAX_UPLOAD_SIZE = 10 * 1024 * 1024

    ALLOWED_IMAGE_TYPES = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    ]

    # Existing cloud provider configuration
    TRANSLATION_SERVICE_URL = os.getenv(
        "TRANSLATION_SERVICE_URL",
        "",
    )

    TRANSLATION_SERVICE_API_KEY = os.getenv(
        "TRANSLATION_SERVICE_API_KEY",
        "",
    )

    # Runpod configuration (kept for future use)
    RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
    RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "")

    RUNPOD_API_BASE = os.getenv(
        "RUNPOD_API_BASE",
        "https://api.runpod.ai/v2",
    )

    RUNPOD_TIMEOUT = int(
        os.getenv("RUNPOD_TIMEOUT", "120")
    )

    # Supported languages
    SUPPORTED_LANGUAGES = [
        "English", "Twi", "Ewe", "Ga", "Dagbani", "Fante",
        "French", "Spanish", "German", "Chinese", "Arabic",
        "Japanese", "Korean", "Portuguese", "Hindi", "Italian",
        "Russian", "Dutch", "Turkish", "Swedish", "Polish",
    ]

        # Text-to-Speech configuration
    OPENAI_TTS_MODEL = os.getenv(
        "OPENAI_TTS_MODEL",
        "gpt-4o-mini-tts",
    )

    OPENAI_TTS_VOICE = os.getenv(
        "OPENAI_TTS_VOICE",
        "alloy",
    )

        # Speech Intelligence configuration
    OPENAI_TRANSCRIPTION_MODEL = os.getenv(
        "OPENAI_TRANSCRIPTION_MODEL",
        "gpt-4o-mini-transcribe",
    )

    OPENAI_TTS_MODEL = os.getenv(
        "OPENAI_TTS_MODEL",
        "gpt-4o-mini-tts",
    )

    OPENAI_TTS_VOICE = os.getenv(
        "OPENAI_TTS_VOICE",
        "alloy",
    )

    SPEECH_MAX_UPLOAD_SIZE = 25 * 1024 * 1024
    SPEECH_MAX_TEXT_LENGTH = 4000
settings = Settings()
