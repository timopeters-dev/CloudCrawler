from bs4 import BeautifulSoup
from parsers.base import BaseParser

class QuoteParser(BaseParser):
    async def parse(self, html: str) -> list:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Finde alle Zitat-Blöcke auf der Seite
        quotes = soup.find_all('div', class_='quote')
        
        for quote in quotes:
            text_tag = quote.find('span', class_='text')
            text = text_tag.text.strip() if text_tag else None
            
            author_tag = quote.find('small', class_='author')
            author = author_tag.text.strip() if author_tag else None
            
            # Alle Tags dieses spezifischen Zitats sammeln
            tags = [tag.text.strip() for tag in quote.find_all('a', class_='tag')]
            
            results.append({
                "type": "quotes",
                "text": text,
                "author": author,
                "tags": tags
            })
            
        return results
