from ai_summarizer import client
from database import pobierz_artykuly
import json

def wykryj_trendy() -> list:
    """Grupuje artykuły w tematy/trendy za pomocą Gemini"""
    artykuly = pobierz_artykuly(50)
    
    if not artykuly:
        return []

    # przygotuj listę artykułów dla AI
    lista = "\n".join([
        f"{i+1}. {a.tytul} | {a.podsumowanie_krotkie or ''}"
        for i, a in enumerate(artykuly)
    ])

    prompt = f"""Masz listę artykułów z czytnika RSS:

{lista}

Pogrupuj je w 3-6 tematycznych trendów. Każdy trend powinien zawierać co najmniej 2 artykuły.

Odpowiedz TYLKO w formacie JSON, bez żadnego dodatkowego tekstu:
[
  {{
    "nazwa": "krótka nazwa trendu (max 5 słów)",
    "opis": "jedno zdanie opisujące trend",
    "artykuly": [1, 3, 5]
  }}
]

Numery artykułów muszą odpowiadać numerom z listy powyżej."""

    odpowiedz = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    tekst = odpowiedz.text.strip()
    # usuń ewentualne backticki markdown
    if tekst.startswith("```"):
        tekst = tekst.split("```")[1]
        if tekst.startswith("json"):
            tekst = tekst[4:]
    tekst = tekst.strip()

    grupy = json.loads(tekst)

    # zamień numery artykułów na prawdziwe dane
    wynik = []
    for grupa in grupy:
        art_w_grupie = []
        for nr in grupa.get("artykuly", []):
            idx = nr - 1
            if 0 <= idx < len(artykuly):
                a = artykuly[idx]
                art_w_grupie.append({
                    "id": a.id,
                    "tytul": a.tytul,
                    "link": a.link,
                    "podsumowanie_krotkie": a.podsumowanie_krotkie,
                    "sentyment": a.sentyment,
                })
        if art_w_grupie:
            wynik.append({
                "nazwa": grupa["nazwa"],
                "opis": grupa["opis"],
                "artykuly": art_w_grupie,
                "liczba": len(art_w_grupie)
            })

    return wynik


if __name__ == "__main__":
    print("Wykrywam trendy...\n")
    trendy = wykryj_trendy()
    for trend in trendy:
        print(f"📌 {trend['nazwa']} ({trend['liczba']} artykułów)")
        print(f"   {trend['opis']}")
        for art in trend['artykuly']:
            print(f"   - {art['tytul']}")
        print()