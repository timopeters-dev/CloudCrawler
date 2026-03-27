from bs4 import BeautifulSoup
from parsers.base import BaseParser

class QuoteParser(BaseParser):
    async def parse(self, html: str) -> list:
        """Extrahiert Zitate von quotes.toscrape.com"""
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for quote in soup.find_all("div", class_="quote"):
            text = el.text.strip() if (el := quote.find("span", class_="text")) else None
            author = el.text.strip() if (el := quote.find("small", class_="author")) else None
            tags = [t.text.strip() for t in quote.find_all("a", class_="tag")]

            results.append({"type": "quotes", "text": text, "author": author, "tags": tags})

        return results
