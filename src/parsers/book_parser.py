import re
from bs4 import BeautifulSoup
from parsers.base import BaseParser

class BookParser(BaseParser):
    async def parse(self, html: str) -> list:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Finde alle Bücher-Kacheln auf der Seite
        articles = soup.find_all('article', class_='product_pod')
        
        for article in articles:
            # Titel extrahieren (aus dem 'title' Attribut des <a> Tags)
            title_tag = article.find('h3').find('a')
            title = title_tag['title'] if title_tag and 'title' in title_tag.attrs else None
            
            # Preis über Regex extrahieren (wie in Übungsblatt 4)
            price_tag = article.find('p', class_='price_color')
            price = None
            if price_tag:
                match = re.search(r'(\d+\.\d+)', price_tag.text)
                if match:
                    price = float(match.group(1))
                    
            results.append({
                "type": "books",
                "title": title,
                "price": price
            })
            
        return results
