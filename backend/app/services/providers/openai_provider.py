
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
    BadRequestError,
)

from app.core.config import settings
from app.services.providers.base_provider import BaseTranslationProvider
from app.services.providers.cloud_provider import (
    TranslationProviderError,
    TranslationProviderUnavailable,
)


class OpenAITranslationProvider(BaseTranslationProvider):

    provider_name = "openai"

    def _get_client(self):
        if not settings.OPENAI_API_KEY:
            raise TranslationProviderUnavailable(
                "OpenAI API key has not been configured."
            )

        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=45.0,
            max_retries=0,
        )

    def detect_language(self, text: str) -> str:
        """Identify the language of the supplied text."""

        try:
            client = self._get_client()

            languages = ", ".join(settings.SUPPORTED_LANGUAGES)

            response = client.responses.create(
                model=settings.OPENAI_MODEL,
                instructions=(
                    "You are TalkBridge's language identification engine. "
                    "Identify the primary language of the supplied text. "
                    "Choose only from the supported language list. "
                    "Return only the exact language name. "
                    "For mixed-language text, identify the dominant language. "
                    "If the text is too short or ambiguous, choose the "
                    "most likely language."
                ),
                input=(
                    f"Supported languages: {languages}\n\n"
                    f"Text:\n{text}"
                ),
            )

            detected = (response.output_text or "").strip()

            if not detected:
                raise TranslationProviderError(
                    "Language detection returned an empty result."
                )

            for language in settings.SUPPORTED_LANGUAGES:
                if detected.casefold() == language.casefold():
                    return language

            raise TranslationProviderError(
                f"Detected language '{detected}' is not supported."
            )

        except AuthenticationError as error:
            raise TranslationProviderUnavailable(
                "OpenAI authentication failed. Check your API key."
            ) from error

        except RateLimitError as error:
            raise TranslationProviderUnavailable(
                "OpenAI API quota or rate limit reached. "
                "Check your API billing."
            ) from error

        except (APITimeoutError, APIConnectionError) as error:
            raise TranslationProviderUnavailable(
                "Language detection timed out or could not connect."
            ) from error

        except BadRequestError as error:
            raise TranslationProviderError(
                "OpenAI rejected the language detection request."
            ) from error

        except APIStatusError as error:
            raise TranslationProviderError(
                f"OpenAI returned HTTP {error.status_code}."
            ) from error

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:

        try:
            client = self._get_client()

            response = client.responses.create(
                model=settings.OPENAI_MODEL,
                instructions=(
                    "You are the translation engine for TalkBridge. "
                    "Translate accurately from the specified source "
                    "language into the specified target language. "
                    "Preserve meaning, tone, names, numbers and formatting. "
                    "Use natural expressions in the target language. "
                    "Return only the translation without explanations."
                ),
                input=(
                    f"Source language: {source_language}\n"
                    f"Target language: {target_language}\n\n"
                    f"Text to translate:\n{text}"
                ),
            )

            translated_text = (response.output_text or "").strip()

            if not translated_text:
                raise TranslationProviderError(
                    "OpenAI returned an empty translation."
                )

            return translated_text

        except AuthenticationError as error:
            raise TranslationProviderUnavailable(
                "OpenAI authentication failed. Check your API key."
            ) from error

        except RateLimitError as error:
            raise TranslationProviderUnavailable(
                "OpenAI API quota or rate limit reached. "
                "Check your API billing."
            ) from error

        except (APITimeoutError, APIConnectionError) as error:
            raise TranslationProviderUnavailable(
                "Translation timed out or could not connect to OpenAI."
            ) from error

        except BadRequestError as error:
            raise TranslationProviderError(
                "OpenAI rejected the translation request."
            ) from error

        except APIStatusError as error:
            raise TranslationProviderError(
                f"OpenAI returned HTTP {error.status_code}."
            ) from error
