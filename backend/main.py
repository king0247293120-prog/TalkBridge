# ============================================================
# TALKBRIDGE BACKEND
# ============================================================
#
# Created by:
# Kingsley Asiedu-Yeboah
# Kumasi Technical University
#
# Stack:
# FastAPI
# Python
# OpenAI API
#
# Features:
# 1. Text translation
# 2. Speech-to-text
# 3. Conversation mode
# 4. Automatic language detection
# 5. Text-to-speech
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import os
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)

from openai import OpenAI

from pydantic import BaseModel


# ============================================================
# LOAD .ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# OPENAI API KEY
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY was not found.\n\n"
        "Create a .env file inside the backend folder "
        "and add:\n\n"
        "OPENAI_API_KEY=your_api_key_here"
    )


# ============================================================
# OPENAI CLIENT
# ============================================================

client = OpenAI(
    api_key=OPENAI_API_KEY
)


# ============================================================
# MODELS
# ============================================================

# Main text model
# Used for:
# - Translation
# - Language detection

TEXT_MODEL = "gpt-6-luna"


# Speech recognition
TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"


# Text-to-speech
TTS_MODEL = "gpt-4o-mini-tts"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TalkBridge API",
    description=(
        "AI-powered multilingual translation backend "
        "for TalkBridge."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================
#
# IMPORTANT:
# The deployed TalkBridge frontend is:
#
# https://talkbridge-sna0.onrender.com
#
# This URL MUST be allowed here so the browser can
# communicate with the backend.
#
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        # LIVE TALKBRIDGE FRONTEND
        "https://talkbridge-sna0.onrender.com",

        # LOCAL DEVELOPMENT
        "http://localhost:5500",
        "http://127.0.0.1:5500",

        "http://localhost:3000",
        "http://127.0.0.1:3000",

        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {

    # --------------------------------------------------------
    # International languages
    # --------------------------------------------------------

    "en": "English",

    "zh": "Chinese",

    "es": "Spanish",

    "fr": "French",

    "de": "German",

    "pt": "Portuguese",

    "ar": "Arabic",

    "ja": "Japanese",

    "ko": "Korean",

    "it": "Italian",

    "ru": "Russian",

    "hi": "Hindi",

    "tr": "Turkish",

    "nl": "Dutch",

    "sv": "Swedish",

    "pl": "Polish",

    # --------------------------------------------------------
    # Ghanaian languages
    # --------------------------------------------------------

    "tw": "Twi",

    "ee": "Ewe",

    "gaa": "Ga",

    "dag": "Dagbani",

    "fat": "Fante",
}


# ============================================================
# COMMON TRANSCRIPTION LANGUAGE CODES
# ============================================================

COMMON_TRANSCRIPTION_CODES = {

    "en",
    "zh",
    "es",
    "fr",
    "de",
    "pt",
    "ar",
    "ja",
    "ko",
    "it",
    "ru",
    "hi",
    "tr",
    "nl",
    "sv",
    "pl",
}


# ============================================================
# REQUEST MODELS
# ============================================================

class TranslationRequest(BaseModel):

    text: str

    source_language: str

    target_language: str


class SpeechRequest(BaseModel):

    text: str

    language: str = "English"

    speed: float = 1.0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(text: str) -> str:
    """
    Removes unnecessary spaces and line breaks.
    """

    if not text:
        return ""

    return " ".join(
        text.strip().split()
    )


# ------------------------------------------------------------


def get_language_name(
    language_code: str
) -> str:

    """
    Converts:

        en -> English
        tw -> Twi
        zh -> Chinese
    """

    if not language_code:
        return ""

    return SUPPORTED_LANGUAGES.get(
        language_code.lower().strip(),
        language_code
    )


# ------------------------------------------------------------


def get_language_code(
    language_name: str
) -> str:

    """
    Converts:

        English -> en
        Twi -> tw
        Chinese -> zh
    """

    if not language_name:
        return ""

    value = language_name.strip().lower()

    # Already a code
    if value in SUPPORTED_LANGUAGES:
        return value

    # Language name
    for code, name in SUPPORTED_LANGUAGES.items():

        if value == name.lower():
            return code

    return value


# ------------------------------------------------------------


def validate_language(
    language: str
) -> str:

    """
    Accepts either a language code or a language name.
    """

    if not language:

        raise HTTPException(
            status_code=400,
            detail="Language was not provided."
        )

    language_clean = (
        language
        .strip()
        .lower()
    )

    # Language code
    if language_clean in SUPPORTED_LANGUAGES:

        return SUPPORTED_LANGUAGES[
            language_clean
        ]

    # Language name
    for code, name in SUPPORTED_LANGUAGES.items():

        if language_clean == name.lower():

            return name

    # Allow additional languages
    return language.strip()


# ------------------------------------------------------------


def normalize_language_code(
    value: str
) -> str:

    """
    Cleans the language detection model's response.

    Examples:

        "en" -> "en"

        "English" -> "en"

        "The language is English." -> "en"

        "tw" -> "tw"
    """

    if not value:
        return ""

    value = value.strip().lower()

    # --------------------------------------------------------
    # Look for exact language codes
    # --------------------------------------------------------

    for code in SUPPORTED_LANGUAGES:

        if re.search(
            rf"\b{re.escape(code)}\b",
            value
        ):

            return code

    # --------------------------------------------------------
    # Look for full language names
    # --------------------------------------------------------

    for code, name in SUPPORTED_LANGUAGES.items():

        if name.lower() in value:

            return code

    return value


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():

    return {

        "name": "TalkBridge",

        "version": "1.0.0",

        "message": (
            "TalkBridge backend is running 🚀"
        ),

        "creator": (
            "Kingsley Asiedu-Yeboah"
        ),

        "institution": (
            "Kumasi Technical University"
        ),

        "status": "online",

        "models": {

            "translation": TEXT_MODEL,

            "transcription": TRANSCRIBE_MODEL,

            "text_to_speech": TTS_MODEL,
        },
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {

        "status": "healthy",

        "openai_configured": (
            bool(OPENAI_API_KEY)
        ),

        "translation_model": TEXT_MODEL,

        "transcription_model": (
            TRANSCRIBE_MODEL
        ),

        "tts_model": TTS_MODEL,
    }


# ============================================================
# NORMAL TRANSLATION
# ============================================================

@app.post("/translate")
async def translate(
    request: TranslationRequest
):

    # --------------------------------------------------------
    # Clean input
    # --------------------------------------------------------

    text = clean_text(
        request.text
    )

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Please provide text to translate."
        )

    # --------------------------------------------------------
    # Validate languages
    # --------------------------------------------------------

    source_language = validate_language(
        request.source_language
    )

    target_language = validate_language(
        request.target_language
    )

    # --------------------------------------------------------
    # Same language
    # --------------------------------------------------------

    if (
        source_language.lower()
        == target_language.lower()
    ):

        return {

            "success": True,

            "translation": text,

            "source_language": source_language,

            "target_language": target_language,
        }

    # --------------------------------------------------------
    # Translation prompt
    # --------------------------------------------------------

    prompt = f"""
You are the translation engine for TalkBridge.

Translate the text below from:

SOURCE LANGUAGE:
{source_language}

TO:

TARGET LANGUAGE:
{target_language}

IMPORTANT RULES:

1. Return ONLY the translated text.

2. Do not explain anything.

3. Do not add:
   "Here is the translation"

4. Do not use quotation marks unless
   they are part of the original text.

5. Preserve the meaning of the original text.

6. Preserve names when appropriate.

7. Preserve numbers and dates.

8. Preserve URLs.

9. Preserve technical terms when appropriate.

10. If the original is casual speech,
    keep the translated version natural
    and conversational.

11. If the text contains a question,
    translate the question naturally.

12. If the text contains Ghanaian expressions,
    preserve the intended meaning.

13. Do not summarize.

14. Do not add information.

15. Do not remove important information.

TEXT:

{text}
"""

    # --------------------------------------------------------
    # Call text model
    # --------------------------------------------------------

    try:

        response = client.responses.create(

            model=TEXT_MODEL,

            input=prompt,

            store=False,

            reasoning={
                "effort": "none"
            },
        )

        translation = (
            response.output_text
            .strip()
        )

        if not translation:

            raise HTTPException(
                status_code=500,
                detail=(
                    "The translation model "
                    "returned an empty response."
                )
            )

        return {

            "success": True,

            "translation": translation,

            "source_language": source_language,

            "target_language": target_language,
        }

    except HTTPException:

        raise

    except Exception as e:

        print(
            "TRANSLATION ERROR:",
            repr(e)
        )

        raise HTTPException(

            status_code=500,

            detail=(
                f"Translation failed: {str(e)}"
            ),
        )


# ============================================================
# SPEECH TO TEXT
# ============================================================

@app.post("/speech/transcribe")
async def transcribe_speech(

    file: UploadFile = File(...),

    language: str = Form(""),

):

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file:

        raise HTTPException(

            status_code=400,

            detail=(
                "No audio file was provided."
            ),
        )

    audio_bytes = await file.read()

    if not audio_bytes:

        raise HTTPException(

            status_code=400,

            detail=(
                "The uploaded audio file is empty."
            ),
        )

    # --------------------------------------------------------
    # Determine extension
    # --------------------------------------------------------

    original_filename = (
        file.filename
        or "audio.webm"
    )

    suffix = Path(
        original_filename
    ).suffix

    if not suffix:

        suffix = ".webm"

    temp_path = None

    try:

        # ----------------------------------------------------
        # Save temporary audio file
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(

            delete=False,

            suffix=suffix

        ) as temp_file:

            temp_file.write(
                audio_bytes
            )

            temp_path = temp_file.name

        # ----------------------------------------------------
        # Prepare transcription request
        # ----------------------------------------------------

        transcription_file = open(
            temp_path,
            "rb"
        )

        try:

            transcription_options = {

                "model": TRANSCRIBE_MODEL,

                "file": transcription_file,
            }

            # ------------------------------------------------
            # Use explicit language for common languages
            # ------------------------------------------------

            language_code = (
                language
                .strip()
                .lower()
                if language
                else ""
            )

            if (
                language_code
                in COMMON_TRANSCRIPTION_CODES
            ):

                transcription_options[
                    "language"
                ] = language_code

            # ------------------------------------------------
            # Transcribe
            # ------------------------------------------------

            transcript = (
                client.audio.transcriptions.create(
                    **transcription_options
                )
            )

        finally:

            transcription_file.close()

        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        text = getattr(
            transcript,
            "text",
            ""
        )

        text = clean_text(text)

        if not text:

            raise HTTPException(

                status_code=500,

                detail=(
                    "No speech could be "
                    "detected in the audio."
                ),
            )

        return {

            "success": True,

            "text": text,

            "language": (
                get_language_name(language)
                if language
                else None
            ),
        }

    except HTTPException:

        raise

    except Exception as e:

        print(
            "TRANSCRIPTION ERROR:",
            repr(e)
        )

        raise HTTPException(

            status_code=500,

            detail=(
                f"Speech transcription failed: "
                f"{str(e)}"
            ),
        )

    finally:

        # ----------------------------------------------------
        # Delete temporary file
        # ----------------------------------------------------

        if temp_path:

            try:

                os.remove(
                    temp_path
                )

            except Exception:

                pass


# ============================================================
# CONVERSATION MODE
# ============================================================

@app.post("/conversation/transcribe")
async def conversation_transcribe(

    file: UploadFile = File(...)

):

    # --------------------------------------------------------
    # Validate audio
    # --------------------------------------------------------

    if not file:

        raise HTTPException(

            status_code=400,

            detail=(
                "No conversation audio "
                "was provided."
            ),
        )

    audio_bytes = await file.read()

    if not audio_bytes:

        raise HTTPException(

            status_code=400,

            detail=(
                "The conversation audio "
                "file is empty."
            ),
        )

    # --------------------------------------------------------
    # Determine extension
    # --------------------------------------------------------

    original_filename = (
        file.filename
        or "conversation.webm"
    )

    suffix = Path(
        original_filename
    ).suffix

    if not suffix:

        suffix = ".webm"

    temp_path = None

    try:

        # ----------------------------------------------------
        # Save temporary file
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(

            delete=False,

            suffix=suffix

        ) as temp_file:

            temp_file.write(
                audio_bytes
            )

            temp_path = temp_file.name

        # ----------------------------------------------------
        # STEP 1
        # TRANSCRIBE SPEECH
        # ----------------------------------------------------

        with open(
            temp_path,
            "rb"
        ) as audio_file:

            transcript = (
                client.audio.transcriptions.create(

                    model=TRANSCRIBE_MODEL,

                    file=audio_file,
                )
            )

        text = getattr(
            transcript,
            "text",
            ""
        )

        text = clean_text(text)

        # ----------------------------------------------------
        # Nothing detected
        # ----------------------------------------------------

        if not text:

            return {

                "success": True,

                "text": "",

                "language": "",
            }

        # ----------------------------------------------------
        # STEP 2
        # DETECT LANGUAGE
        # ----------------------------------------------------

        language_prompt = f"""
You are the language detection engine
for TalkBridge.

Identify the language of the text below.

Return ONLY the language code.

Do NOT explain.

Supported languages:

English = en
Chinese = zh
Spanish = es
French = fr
German = de
Portuguese = pt
Arabic = ar
Japanese = ja
Korean = ko
Italian = it
Russian = ru
Hindi = hi
Turkish = tr
Dutch = nl
Swedish = sv
Polish = pl

Ghanaian languages:

Twi = tw
Ewe = ee
Ga = gaa
Dagbani = dag
Fante = fat

IMPORTANT:

- If it is English, return en.
- If it is Chinese, return zh.
- If it is Spanish, return es.
- If it is French, return fr.
- If it is German, return de.
- If it is Portuguese, return pt.
- If it is Arabic, return ar.
- If it is Japanese, return ja.
- If it is Korean, return ko.
- If it is Italian, return it.
- If it is Russian, return ru.
- If it is Hindi, return hi.
- If it is Turkish, return tr.
- If it is Dutch, return nl.
- If it is Swedish, return sv.
- If it is Polish, return pl.
- If it is Twi, return tw.
- If it is Ewe, return ee.
- If it is Ga, return gaa.
- If it is Dagbani, return dag.
- If it is Fante, return fat.

Return ONLY the code.

TEXT:

{text}
"""

        # ----------------------------------------------------
        # Ask text model
        # ----------------------------------------------------

        language_response = (
            client.responses.create(

                model=TEXT_MODEL,

                input=language_prompt,

                store=False,

                reasoning={
                    "effort": "none"
                },
            )
        )

        detected_language = (
            normalize_language_code(
                language_response.output_text
            )
        )

        # ----------------------------------------------------
        # Return
        # ----------------------------------------------------

        return {

            "success": True,

            "text": text,

            "language": detected_language,
        }

    except Exception as e:

        print(
            "CONVERSATION ERROR:",
            repr(e)
        )

        raise HTTPException(

            status_code=500,

            detail=(
                "Conversation transcription "
                f"failed: {str(e)}"
            ),
        )

    finally:

        # ----------------------------------------------------
        # Remove temporary file
        # ----------------------------------------------------

        if temp_path:

            try:

                os.remove(
                    temp_path
                )

            except Exception:

                pass


# ============================================================
# TEXT TO SPEECH
# ============================================================

@app.post("/speech")
async def text_to_speech(
    request: SpeechRequest
):

    # --------------------------------------------------------
    # Clean text
    # --------------------------------------------------------

    text = clean_text(
        request.text
    )

    if not text:

        raise HTTPException(

            status_code=400,

            detail=(
                "No text was provided "
                "for speech generation."
            ),
        )

    # --------------------------------------------------------
    # Limit speed
    # --------------------------------------------------------

    speed = max(

        0.25,

        min(
            request.speed,
            4.0
        ),
    )

    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    language = validate_language(
        request.language
    )

    # --------------------------------------------------------
    # Instructions
    # --------------------------------------------------------

    instructions = f"""
Speak the following text naturally.

Target language:
{language}

Speak clearly and naturally.

Do not translate the text again.

Do not add any extra words.

Do not introduce the speech.

Simply speak the provided text.
"""

    try:

        # ----------------------------------------------------
        # Generate speech
        # ----------------------------------------------------

        audio_response = (
            client.audio.speech.create(

                model=TTS_MODEL,

                voice="alloy",

                input=text,

                instructions=instructions,

                response_format="mp3",

                speed=speed,
            )
        )

        # ----------------------------------------------------
        # Read audio
        # ----------------------------------------------------

        audio_data = (
            audio_response.read()
        )

        if not audio_data:

            raise HTTPException(

                status_code=500,

                detail=(
                    "The speech model "
                    "returned empty audio."
                ),
            )

        # ----------------------------------------------------
        # Return MP3
        # ----------------------------------------------------

        return StreamingResponse(

            iter([audio_data]),

            media_type="audio/mpeg",

            headers={

                "Content-Disposition":
                    "inline; "
                    "filename=talkbridge.mp3"
            },
        )

    except HTTPException:

        raise

    except Exception as e:

        print(
            "TEXT TO SPEECH ERROR:",
            repr(e)
        )

        raise HTTPException(

            status_code=500,

            detail=(
                f"Text-to-speech failed: "
                f"{str(e)}"
            ),
        )


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request,
    exc
):

    print(
        "UNHANDLED SERVER ERROR:",
        repr(exc)
    )

    return JSONResponse(

        status_code=500,

        content={

            "success": False,

            "error": (
                "An unexpected server "
                "error occurred."
            ),

            "detail": str(exc),
        },
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("")

    print("=" * 65)

    print(
        "                 TALKBRIDGE"
    )

    print("=" * 65)

    print(
        "Status: ONLINE"
    )

    print(
        f"Translation model: {TEXT_MODEL}"
    )

    print(
        f"Transcription model: "
        f"{TRANSCRIBE_MODEL}"
    )

    print(
        f"TTS model: {TTS_MODEL}"
    )

    print(
        "API key: CONFIGURED"
    )

    print("=" * 65)

    print("")

    print(
        "TalkBridge API is ready."
    )

    print("")
