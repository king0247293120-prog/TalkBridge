
from abc import ABC, abstractmethod


class BaseTranslationProvider(ABC):
    """
    Common interface for all TalkBridge translation providers.
    Every translation model adapter must implement this method.
    """

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        pass
