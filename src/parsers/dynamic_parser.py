from bs4 import BeautifulSoup

class DynamicParser:
    async def parse(self, html: str, selectors: dict) -> dict:
        """
        Nimmt HTML und ein Dictionary mit CSS-Selektoren.
        Beispiel selectors: {"titel": "h1", "preis": "p.price_color"}
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = {"type": "dynamic_custom"}
        
        for field_name, css_selector in selectors.items():
            element = soup.select_one(css_selector)
            # Wenn das Element gefunden wird, Text extrahieren, sonst None
            result[field_name] = element.text.strip() if element else None
            
        return result
