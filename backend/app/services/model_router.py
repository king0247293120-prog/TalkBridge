
from app.core.config import settings

from app.services.providers.cloud_provider import (
    CloudTranslationProvider,
    TranslationProviderUnavailable,
)

from app.services.providers.runpod_provider import (
    RunpodTranslationProvider,
)

from app.services.providers.openai_provider import (
    OpenAITranslationProvider,
)


def get_translation_provider():

    provider_name = settings.TRANSLATION_PROVIDER.lower()

    if provider_name == "openai":
        return OpenAITranslationProvider()

    if provider_name == "cloud":
        return CloudTranslationProvider()

    if provider_name == "runpod_serverless":
        return RunpodTranslationProvider()

    raise TranslationProviderUnavailable(
        f"Translation provider '{provider_name}' "
        "is not supported or configured."
    )
