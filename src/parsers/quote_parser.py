from .base import BaseParser
from bs4 import BeautifulSoup

class QuoteParser(BaseParser):
    async def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Wir nehmen das erste Zitat auf der Seite
        first_quote = soup.find('div', class_='quote')
        if not first_quote:
            return {}
            
        return {
            "text": first_quote.find('span', class_='text').text,
            "author": first_quote.find('small', class_='author').text,
            "tags": [tag.text for tag in first_quote.find_all('a', class_='tag')],
            "type": "quote" # Damit wir in der DB wissen, was es ist
        }
