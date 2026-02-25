from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, html: str) -> dict:
        """Extrahiert Daten aus dem HTML und gibt ein Dict zurück."""
        pass
