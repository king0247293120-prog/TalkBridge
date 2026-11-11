
import httpx

from app.services.providers.base_provider import BaseTranslationProvider
from app.core.config import settings


class TranslationProviderError(Exception):
    pass


class TranslationProviderUnavailable(Exception):
    pass


class CloudTranslationProvider(BaseTranslationProvider):

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:

        service_url = settings.TRANSLATION_SERVICE_URL

        if not service_url:
            raise TranslationProviderUnavailable(
                "Cloud translation service has not been configured."
            )

        headers = {
            "Content-Type": "application/json"
        }

        if settings.TRANSLATION_SERVICE_API_KEY:
            headers["Authorization"] = (
                f"Bearer {settings.TRANSLATION_SERVICE_API_KEY}"
            )

        payload = {
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
            "model": settings.TRANSLATION_MODEL,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    service_url,
                    json=payload,
                    headers=headers,
                )

            response.raise_for_status()

            result = response.json()
            translated_text = result.get("translated_text")

            if not isinstance(translated_text, str):
                raise TranslationProviderError(
                    "Cloud model returned an invalid response."
                )

            if not translated_text.strip():
                raise TranslationProviderError(
                    "Cloud model returned an empty translation."
                )

            return translated_text.strip()

        except httpx.TimeoutException as error:
            raise TranslationProviderUnavailable(
                "Cloud translation service timed out."
            ) from error

        except httpx.HTTPStatusError as error:
            raise TranslationProviderError(
                f"Cloud translation service returned HTTP "
                f"{error.response.status_code}."
            ) from error

        except httpx.RequestError as error:
            raise TranslationProviderUnavailable(
                "Could not connect to the cloud translation service."
            ) from error

        except ValueError as error:
            raise TranslationProviderError(
                "Cloud translation service returned invalid JSON."
            ) from error
