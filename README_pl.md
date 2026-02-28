# 🧠 CognitoFeed

Inteligentny czytnik RSS wspomagany przez AI (Google Gemini).

## Funkcje
- 📰 Subskrypcja kanałów RSS/Atom
- 💬 Automatyczne podsumowania AI (krótkie i średnie)
- 🎭 Analiza sentymentu artykułów
- 📌 Wykrywanie trendów tematycznych
- ⭐ Ulubione artykuły
- 📖 Tryb czytania (Reader View)
- 🔔 Powiadomienia o nowych artykułach
- 🔄 Auto-odświeżanie kanałów
- 🤖 Czat AI z kontekstem artykułów

## Wymagania
- Python 3.11+
- Klucz API Google AI Studio (Gemini)

## Instalacja

```bash
git clone https://github.com/TWOJ_LOGIN/CognitoFeed.git
cd CognitoFeed
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Stwórz plik `.env`:
```
GEMINI_API_KEY=twoj_klucz_api
```

## Uruchomienie

```bash
# Pierwsze uruchomienie - pobierz artykuły
python main.py

# Uruchom serwer
uvicorn api:app --reload
```

Otwórz http://localhost:8000 w przeglądarce.

## Stack
- **Backend:** Python + FastAPI
- **Baza danych:** SQLite
- **AI:** Google Gemini 2.5 Flash
- **Frontend:** HTML/CSS/JS
