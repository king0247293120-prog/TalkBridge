from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.writing_service import (
    process_writing,
    WritingServiceError,
    WritingServiceUnavailable,
)


router = APIRouter(
    prefix="/writing",
    tags=["Writing Intelligence"],
)


class WritingRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
    )

    task: Literal[
        "correct",
        "paraphrase",
        "rewrite",
        "summarize",
        "expand",
        "shorten",
        "change_tone",
        "improve_clarity",
    ]

    tone: str | None = Field(
        default=None,
        max_length=100,
    )

    length: Literal[
        "short",
        "medium",
        "detailed",
    ] = "medium"

    language: str = Field(
        default="English",
        min_length=1,
        max_length=50,
    )


@router.get("/tools")
def get_writing_tools():
    return {
        "department": "Writing Intelligence",
        "status": "available",
        "tools": [
            {
                "id": "correct",
                "name": "Grammar and spelling correction",
            },
            {
                "id": "paraphrase",
                "name": "Paraphrasing",
            },
            {
                "id": "rewrite",
                "name": "Rewriting",
            },
            {
                "id": "summarize",
                "name": "Summarization",
            },
            {
                "id": "expand",
                "name": "Expand text",
            },
            {
                "id": "shorten",
                "name": "Shorten text",
            },
            {
                "id": "change_tone",
                "name": "Change writing tone",
            },
            {
                "id": "improve_clarity",
                "name": "Improve clarity",
            },
        ],
    }


@router.post("/process")
async def writing_process(request: WritingRequest):

    original_text = request.text.strip()

    if not original_text:
        raise HTTPException(
            status_code=400,
            detail="Please provide text to process.",
        )

    if (
        request.task == "change_tone"
        and not request.tone
    ):
        raise HTTPException(
            status_code=400,
            detail="Please specify the tone you want.",
        )

    try:
        processed_text = await process_writing(
            text=original_text,
            task=request.task,
            tone=request.tone,
            length=request.length,
            language=request.language,
        )

        return {
            "status": "success",
            "department": "Writing Intelligence",
            "task": request.task,
            "language": request.language,
            "original_text": original_text,
            "processed_text": processed_text,
            "model": settings.OPENAI_MODEL,
        }

    except WritingServiceUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except WritingServiceError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected writing error occurred.",
        )
