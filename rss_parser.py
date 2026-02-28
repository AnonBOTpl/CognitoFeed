import feedparser
import asyncio
from datetime import datetime
from database import zapisz_kanal, pobierz_artykuly

async def fetch_feed(url: str) -> dict:
    """Pobiera i parsuje kanał RSS z podanego URL"""
    feed = feedparser.parse(url)
    
    if feed.bozo:
        print(f"Błąd parsowania: {url}")
        return None
    
    kanal = {
        "tytuł": feed.feed.get("title", "Brak tytułu"),
        "url": url,
        "opis": feed.feed.get("description", ""),
        "artykuły": []
    }
    
    for wpis in feed.entries[:10]:
        artykul = {
            "tytuł": wpis.get("title", "Brak tytułu"),
            "link": wpis.get("link", ""),
            "opis": wpis.get("summary", ""),
            "data": wpis.get("published", str(datetime.now())),
        }
        kanal["artykuły"].append(artykul)
    
    return kanal

async def main():
    url = "https://feeds.bbci.co.uk/news/rss.xml"
    wynik = await fetch_feed(url)
    
    if wynik:
        print(f"Kanał: {wynik['tytuł']}")
        zapisz_kanal(wynik)
        
        print("\nArtykuły w bazie:")
        for art in pobierz_artykuly():
            print(f"  - {art.tytul}")

if __name__ == "__main__":
    asyncio.run(main())