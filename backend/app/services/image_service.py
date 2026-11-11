
import base64

from openai import (
    AsyncOpenAI,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
    BadRequestError,
)

from app.core.config import settings


class ImageServiceError(Exception):
    pass


class ImageServiceUnavailable(Exception):
    pass


async def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    question: str = "Describe this image in detail.",
) -> str:

    if not settings.OPENAI_API_KEY:
        raise ImageServiceUnavailable(
            "OpenAI API key has not been configured."
        )

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    image_data_url = (
        f"data:{mime_type};base64,{encoded_image}"
    )

    try:
        client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=45.0,
    max_retries=0,
)

        response = await client.responses.create(
            model=settings.OPENAI_VISION_MODEL,
            instructions=(
                "You are TalkBridge Image Intelligence. "
                "Analyze images carefully and answer the user's "
                "question accurately. Describe visible details, "
                "identify objects when possible, and extract "
                "visible text when requested. Do not invent "
                "details that cannot be seen."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": question,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "auto",
                        },
                    ],
                }
            ],
        )

        result = response.output_text

        if not result or not result.strip():
            raise ImageServiceError(
                "The vision model returned an empty response."
            )

        return result.strip()

    except AuthenticationError as error:
        raise ImageServiceUnavailable(
            "OpenAI authentication failed. Check your API key."
        ) from error

    except RateLimitError as error:
        raise ImageServiceUnavailable(
            "OpenAI quota or rate limit reached. Check API billing."
        ) from error

    except (APITimeoutError, APIConnectionError) as error:
        raise ImageServiceUnavailable(
            "Could not connect to OpenAI or the request timed out."
        ) from error

    except BadRequestError as error:
        raise ImageServiceError(
            "OpenAI rejected the image request. Check the image "
            "format and vision model configuration."
        ) from error

    except APIStatusError as error:
        raise ImageServiceError(
            f"OpenAI returned HTTP {error.status_code}."
        ) from error

async def extract_image_text(
    image_bytes: bytes,
    mime_type: str,
) -> str:

    if not settings.OPENAI_API_KEY:
        raise ImageServiceUnavailable(
            "OpenAI API key has not been configured."
        )

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    image_data_url = f"data:{mime_type};base64,{encoded_image}"

    try:
        client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=45.0,
    max_retries=0,
)

        response = await client.responses.create(
            model=settings.OPENAI_VISION_MODEL,
            instructions=(
                "You are TalkBridge OCR, an accurate text extraction "
                "engine. Extract all readable text from the supplied "
                "image. Preserve the original language, spelling, "
                "numbers, punctuation and paragraph structure. "
                "Keep headings and lists on separate lines. "
                "Do not translate, summarize, correct or explain "
                "the text. Do not invent missing words. If a section "
                "is unreadable, indicate [unreadable]. Return only "
                "the extracted text."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Extract all readable text from this image.",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
        )

        extracted_text = response.output_text

        if not extracted_text or not extracted_text.strip():
            raise ImageServiceError(
                "No readable text was found in the image."
            )

        return extracted_text.strip()

    except AuthenticationError as error:
        raise ImageServiceUnavailable(
            "OpenAI authentication failed. Check your API key."
        ) from error

    except RateLimitError as error:
        raise ImageServiceUnavailable(
            "OpenAI quota or rate limit reached. Check API billing."
        ) from error

    except (APITimeoutError, APIConnectionError) as error:
        raise ImageServiceUnavailable(
            "Could not connect to OpenAI or the request timed out."
        ) from error

    except BadRequestError as error:
        raise ImageServiceError(
            "OpenAI rejected the OCR request. Check the image and model."
        ) from error

    except APIStatusError as error:
        raise ImageServiceError(
            f"OpenAI returned HTTP {error.status_code}."
        ) from error
