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


class WritingServiceError(Exception):
    pass


class WritingServiceUnavailable(Exception):
    pass


WRITING_INSTRUCTIONS = """
You are TalkBridge Writing Intelligence.

Your job is to improve, transform and assist with written content.

Rules:
1. Preserve the original meaning and intended message.
2. Do not invent facts, names, dates, statistics or references.
3. Preserve important technical terms and proper nouns.
4. Correct grammar, spelling and punctuation when appropriate.
5. Follow the requested writing task and tone.
6. Do not add explanations unless the user requests them.
7. Return the final written content only.
"""


TASK_INSTRUCTIONS = {
    "correct": (
        "Correct grammar, spelling, punctuation and sentence structure. "
        "Keep the original meaning, wording and style as much as possible."
    ),
    "paraphrase": (
        "Paraphrase the text using different wording while preserving "
        "its original meaning and important details."
    ),
    "rewrite": (
        "Rewrite the text to make it more effective, natural and well "
        "structured while preserving its original message."
    ),
    "summarize": (
        "Summarize the text. Retain its most important ideas, facts "
        "and conclusions."
    ),
    "expand": (
        "Expand the text with clearer explanations and better-developed "
        "sentences. Do not invent facts or unsupported information."
    ),
    "shorten": (
        "Make the text shorter and more concise while preserving "
        "its essential meaning and information."
    ),
    "change_tone": (
        "Rewrite the text using the requested tone while preserving "
        "its original meaning."
    ),
    "improve_clarity": (
        "Improve clarity, readability, flow and sentence structure. "
        "Make the text easier to understand without changing its meaning."
    ),
}


async def process_writing(
    text: str,
    task: str,
    tone: str | None = None,
    length: str = "medium",
    language: str = "English",
) -> str:

    if not settings.OPENAI_API_KEY:
        raise WritingServiceUnavailable(
            "Writing service is not configured."
        )

    if task not in TASK_INSTRUCTIONS:
        raise WritingServiceError(
            "Unsupported writing task."
        )

    task_instruction = TASK_INSTRUCTIONS[task]

    if task == "change_tone":
        if not tone or not tone.strip():
            raise WritingServiceError(
                "Please provide the tone you want."
            )

        task_instruction += f"\nRequested tone: {tone.strip()}."

    if task == "summarize":
        task_instruction += f"\nSummary length: {length}."

    user_prompt = f"""
Writing task:
{task_instruction}

Output language:
{language}

Original text:
<text>
{text}
</text>

Return only the completed writing.
"""

    try:
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT,
        )

        response = await client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=WRITING_INSTRUCTIONS,
            input=user_prompt,
        )

        result = response.output_text

        if not result or not result.strip():
            raise WritingServiceError(
                "The writing model returned an empty response."
            )

        return result.strip()

    except AuthenticationError:
        raise WritingServiceUnavailable(
            "The writing service authentication failed."
        )

    except RateLimitError:
        raise WritingServiceUnavailable(
            "The writing service is currently rate limited. Please try again later."
        )

    except (APIConnectionError, APITimeoutError):
        raise WritingServiceUnavailable(
            "Unable to connect to the writing service."
        )

    except BadRequestError as error:
        raise WritingServiceError(
            f"The writing request was rejected: {error}"
        )

    except APIStatusError:
        raise WritingServiceUnavailable(
            "The writing provider returned a service error."
        )
