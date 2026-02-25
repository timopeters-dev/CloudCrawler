import re
from .base import BaseParser
from bs4 import BeautifulSoup

class BookParser(BaseParser):
    async def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        book = soup.find('article', class_='product_pod')
        if not book:
            return {}

        raw_price = book.find('p', class_='price_color').text
        
        # --- REGEX ACTION ---
        # Wir suchen nach einer Zahl, gefolgt von einem Punkt und zwei Dezimalstellen
        # Entspricht Aufgabe 1 & 5 aus deinem Übungsblatt!
        price_match = re.search(r'(\d+\.\d+)', raw_price)
        price_float = float(price_match.group(1)) if price_match else 0.0

        return {
            "title": book.h3.a['title'],
            "price": price_float,  # Jetzt als echte Zahl (float)
            "currency": "GBP",
            "type": "book"
        }
