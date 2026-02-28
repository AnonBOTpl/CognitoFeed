import asyncio
from rss_parser import fetch_feed
from database import zapisz_kanal, zapisz_podsumowanie, zapisz_kategorie, pobierz_artykuly
from ai_summarizer import podsumuj_artykul, przypisz_kategorie

KANALY = [
    "https://feeds.bbci.co.uk/news/rss.xml",
]

async def przetworz_kanal(url: str):
    print(f"\nPobieram: {url}")
    dane = await fetch_feed(url)

    if not dane:
        return

    nowe = zapisz_kanal(dane)

    if not nowe:
        print("Brak nowych artykułów")
        return

    print(f"Generuję podsumowania AI dla {len(nowe)} artykułów...")
    for artykul in nowe:
        print(f"  Przetwarzam: {artykul['tytul'][:60]}...")
        podsumowania = podsumuj_artykul(artykul["tytul"], artykul["opis"] or "")
        zapisz_podsumowanie(artykul["link"], podsumowania)
        kategoria = przypisz_kategorie(artykul["tytul"], artykul["opis"] or "")
        zapisz_kategorie(artykul["link"], kategoria)
        print(f"    Kategoria: {kategoria}")

    print("\nGotowe! Artykuły z podsumowaniami:")
    for art in pobierz_artykuly(5):
        print(f"\n📰 [{art.kategoria}] {art.tytul}")
        print(f"   💬 {art.podsumowanie_krotkie}")

async def main():
    for url in KANALY:
        await przetworz_kanal(url)

if __name__ == "__main__":
    asyncio.run(main())