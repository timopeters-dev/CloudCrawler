from .base import BaseParser
from bs4 import BeautifulSoup

class BookParser(BaseParser):
    async def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        # Wir suchen das erste Buch als Beispiel
        book = soup.find('article', class_='product_pod')
        if not book:
            return {}
            
        return {
            "title": book.h3.a['title'],
            "price": book.find('p', class_='price_color').text,
            "type": "book"
        }
