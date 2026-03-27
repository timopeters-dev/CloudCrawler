import re
from bs4 import BeautifulSoup
from parsers.base import BaseParser

class BookParser(BaseParser):
    async def parse(self, html: str) -> list:
        """Extrahiert Buchdaten von books.toscrape.com"""
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for article in soup.find_all("article", class_="product_pod"):
            title_tag = article.find("h3").find("a")
            title = title_tag["title"] if title_tag and "title" in title_tag.attrs else None

            price_tag = article.find("p", class_="price_color")
            price = None
            if price_tag and (match := re.search(r"(\d+\.\d+)", price_tag.text)):
                price = float(match.group(1))

            results.append({"type": "books", "title": title, "price": price})

        return results
