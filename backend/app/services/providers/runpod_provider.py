import httpx

from app.core.config import settings
from app.services.providers.base_provider import BaseTranslationProvider


class RunpodProviderError(Exception):
    pass


class RunpodProviderUnavailable(Exception):
    pass


class RunpodTranslationProvider(BaseTranslationProvider):

    provider_name = "runpod_serverless"

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:

        if not settings.RUNPOD_API_KEY:
            raise RunpodProviderUnavailable(
                "Runpod API key has not been configured."
            )

        if not settings.RUNPOD_ENDPOINT_ID:
            raise RunpodProviderUnavailable(
                "Runpod endpoint ID has not been configured."
            )

        url = (
            f"{settings.RUNPOD_API_BASE.rstrip('/')}/"
            f"{settings.RUNPOD_ENDPOINT_ID}/runsync"
        )

        headers = {
            "Authorization": f"Bearer {settings.RUNPOD_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "input": {
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
                "model": settings.TRANSLATION_MODEL,
            }
        }

        try:
            with httpx.Client(
                timeout=settings.RUNPOD_TIMEOUT
            ) as client:

                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()
                result = response.json()

            if not isinstance(result, dict):
                raise RunpodProviderError(
                    "Runpod returned an invalid response."
                )

            output = result.get("output")

            if not isinstance(output, dict):
                raise RunpodProviderError(
                    "Runpod did not return a valid translation output."
                )

            translated_text = output.get("translated_text")

            if not isinstance(translated_text, str):
                raise RunpodProviderError(
                    "The model did not return translated_text."
                )

            if not translated_text.strip():
                raise RunpodProviderError(
                    "The model returned an empty translation."
                )

            return translated_text.strip()

        except httpx.TimeoutException as error:
            raise RunpodProviderUnavailable(
                "Runpod translation request timed out."
            ) from error

        except httpx.HTTPStatusError as error:
            raise RunpodProviderError(
                f"Runpod returned HTTP "
                f"{error.response.status_code}."
            ) from error

        except httpx.RequestError as error:
            raise RunpodProviderUnavailable(
                "Could not connect to Runpod."
            ) from error

        except ValueError as error:
            raise RunpodProviderError(
                "Runpod returned invalid JSON."
            ) from error