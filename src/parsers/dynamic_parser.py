from bs4 import BeautifulSoup


class DynamicParser:
    async def parse(self, html: str, selectors: dict) -> list:
        """
        Extrahiert alle gefundenen Elemente und gibt eine Liste von Dictionaries zurück.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Alle Elemente pro Selektor in Listen sammeln
        extracted_data = {}
        max_length = 0

        for field_name, css_selector in selectors.items():
            elements = soup.select(css_selector)
            # Extrahiere den Text aus jedem gefundenen Element
            texts = [el.text.strip() for el in elements]
            extracted_data[field_name] = texts

            # Merken, was die längste gefundene Liste ist (z.B. 20 Bücher)
            if len(texts) > max_length:
                max_length = len(texts)

        # 2. Die gesammelten Spalten zu einzelnen Objekten (Zeilen) "zippen"
        results = []
        for i in range(max_length):
            item = {"type": "dynamic_custom"}
            for field_name in selectors.keys():
                # Falls eine Liste kürzer ist (z.B. ein Buch hat keinen Autor), trage None ein
                item[field_name] = (
                    extracted_data[field_name][i]
                    if i < len(extracted_data[field_name])
                    else None
                )
            results.append(item)

        return results  # Wir geben jetzt eine Liste zurück!
