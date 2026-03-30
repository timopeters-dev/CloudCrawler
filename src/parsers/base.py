from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, html: str, *args, **kwargs):
        """Extrahiert Daten aus dem HTML."""
        pass
