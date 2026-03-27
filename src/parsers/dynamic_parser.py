from bs4 import BeautifulSoup

class DynamicParser:
    async def parse(self, html: str, selectors: dict, row_selector: str = None) -> list:
        """
        Extrahiert Daten basierend auf flexiblen CSS-Selektoren.
        Unterstützt Listen (via row_selector) oder Einzelwerte (Standard).
        """
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(row_selector) if row_selector else [soup]

        results = []
        for container in containers:
            item = {
                name: (el.text.strip() if (el := container.select_one(sel)) else None)
                for name, sel in selectors.items()
            }
            if any(item.values()):
                results.append(item)

        return results
