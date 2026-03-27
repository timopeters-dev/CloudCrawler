from bs4 import BeautifulSoup


class DynamicParser:
    async def parse(self, html: str, selectors: dict, row_selector: str = None) -> list:
        """
        Extrahiert Daten mit einem "Box-in-Box" Ansatz.
        - row_selector: Wenn vorhanden, werden alle Vorkommen gesucht (z.B. 'tr' für Tabellenzeilen).
        - selectors: Dictionary mit Feldname -> CSS Selektor (relativ zur Row).
        """
        soup = BeautifulSoup(html, "html.parser")

        # Bestimme die Container (Rows)
        if row_selector:
            containers = soup.select(row_selector)
        else:
            # Fallback: Das ganze Dokument ist ein einziger Container
            containers = [soup]

        results = []
        for container in containers:
            item = {}
            for field_name, css_selector in selectors.items():
                element = container.select_one(css_selector)
                item[field_name] = element.text.strip() if element else None

            # Nur hinzufügen, wenn mindestens ein Feld gefunden wurde
            if any(value is not None for value in item.values()):
                results.append(item)

        return results
