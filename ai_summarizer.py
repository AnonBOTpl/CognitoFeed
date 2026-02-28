from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def podsumuj_artykul(tytul: str, tresc: str) -> dict:
    """Generuje podsumowania artykułu na trzech poziomach"""
    
    prompt = f"""Artykuł:
Tytuł: {tytul}
Treść: {tresc}

Wygeneruj trzy podsumowania w języku polskim:
1. KROTKIE: jedno zdanie (max 20 słów)
2. SREDNIE: jeden akapit (max 60 słów)  
3. SENTYMENT: czy artykuł jest pozytywny/negatywny/neutralny i dlaczego (jedno zdanie)

Odpowiedz w formacie:
KROTKIE: ...
SREDNIE: ...
SENTYMENT: ..."""

    odpowiedz = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    tekst = odpowiedz.text
    
    wynik = {}
    for linia in tekst.strip().split("\n"):
        if linia.startswith("KROTKIE:"):
            wynik["krotkie"] = linia.replace("KROTKIE:", "").strip()
        elif linia.startswith("SREDNIE:"):
            wynik["srednie"] = linia.replace("SREDNIE:", "").strip()
        elif linia.startswith("SENTYMENT:"):
            wynik["sentyment"] = linia.replace("SENTYMENT:", "").strip()
    
    return wynik

if __name__ == "__main__":
    tytul = "UK planes in the sky in Middle East as part of defensive operation"
    tresc = "British military aircraft are operating in the Middle East as part of a defensive operation following Iranian strikes on Israel."
    
    print("Generuję podsumowanie...\n")
    wynik = podsumuj_artykul(tytul, tresc)
    
    print(f"KRÓTKIE: {wynik.get('krotkie')}")
    print(f"ŚREDNIE: {wynik.get('srednie')}")
    print(f"SENTYMENT: {wynik.get('sentyment')}")