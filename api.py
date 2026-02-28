from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import pobierz_artykuly, pobierz_ulubione, przelacz_ulubiony, pobierz_kategorie, pobierz_artykuly_kategorii, zapisz_kategorie, Session, Kanal, Artykul, zapisz_kanal, zapisz_podsumowanie
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio

# --- Auto-odświeżanie ---
INTERWAL_MINUT = 30  # co ile minut odświeżać kanały
odswiezanie_aktywne = True

async def auto_odswiez():
    """Automatycznie odświeża kanały co INTERWAL_MINUT minut"""
    while odswiezanie_aktywne:
        await asyncio.sleep(INTERWAL_MINUT * 60)
        print(f"[Auto] Odświeżam kanały...")
        try:
            from rss_parser import fetch_feed
            from ai_summarizer import podsumuj_artykul

            session = Session()
            kanaly = session.query(Kanal).all()
            urls = [k.url for k in kanaly]
            session.close()

            lacznie = 0
            for url in urls:
                wynik = await fetch_feed(url)
                if not wynik:
                    continue
                nowe = zapisz_kanal(wynik)
                for art in nowe:
                    podsumowania = podsumuj_artykul(art["tytul"], art["opis"] or "")
                    zapisz_podsumowanie(art["link"], podsumowania)
                lacznie += len(nowe)

            print(f"[Auto] Gotowe! Nowych artykułów: {lacznie}")
        except Exception as e:
            print(f"[Auto] Błąd: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # start – uruchom auto-odświeżanie w tle
    task = asyncio.create_task(auto_odswiez())
    yield
    # stop – zatrzymaj przy zamknięciu serwera
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/artykuly")
def get_artykuly(limit: int = 50):
    artykuly = pobierz_artykuly(limit)
    wynik = []
    for art in artykuly:
        wynik.append({
            "id": art.id,
            "tytul": art.tytul,
            "link": art.link,
            "kanal_url": art.kanal_url,
            "data_publikacji": art.data_publikacji,
            "podsumowanie_krotkie": art.podsumowanie_krotkie,
            "podsumowanie_srednie": art.podsumowanie_srednie,
            "sentyment": art.sentyment,
        })
    return wynik

@app.get("/api/artykuly/kanal")
def get_artykuly_kanalu(url: str, limit: int = 50):
    session = Session()
    artykuly = session.query(Artykul).filter_by(kanal_url=url).order_by(Artykul.dodano.desc()).limit(limit).all()
    session.close()
    wynik = []
    for art in artykuly:
        wynik.append({
            "id": art.id,
            "tytul": art.tytul,
            "link": art.link,
            "kanal_url": art.kanal_url,
            "data_publikacji": art.data_publikacji,
            "podsumowanie_krotkie": art.podsumowanie_krotkie,
            "podsumowanie_srednie": art.podsumowanie_srednie,
            "sentyment": art.sentyment,
        })
    return wynik

@app.get("/api/kanaly")
def get_kanaly():
    session = Session()
    kanaly = session.query(Kanal).all()
    wynik = [{"id": k.id, "tytul": k.tytul, "url": k.url} for k in kanaly]
    session.close()
    return wynik

@app.get("/api/ustawienia/interwal")
def get_interwal():
    return {"interwał_minut": INTERWAL_MINUT}

@app.post("/api/ustawienia/interwal")
def set_interwal(dane: dict):
    global INTERWAL_MINUT
    INTERWAL_MINUT = int(dane.get("interwał_minut", 30))
    return {"sukces": True, "interwał_minut": INTERWAL_MINUT}

class KanalURL(BaseModel):
    url: str

@app.post("/api/kanaly/dodaj")
async def dodaj_kanal(dane: KanalURL):
    from rss_parser import fetch_feed
    from ai_summarizer import podsumuj_artykul

    wynik = await fetch_feed(dane.url)
    if not wynik:
        return {"sukces": False, "komunikat": "Nie udało się pobrać kanału – sprawdź URL"}

    nowe = zapisz_kanal(wynik)
    for art in nowe:
        podsumowania = podsumuj_artykul(art["tytul"], art["opis"] or "")
        zapisz_podsumowanie(art["link"], podsumowania)

    return {
        "sukces": True,
        "komunikat": f"Dodano kanał '{wynik['tytuł']}' z {len(nowe)} nowymi artykułami"
    }

@app.post("/api/odswierz")
async def odswiez():
    from rss_parser import fetch_feed
    from ai_summarizer import podsumuj_artykul

    session = Session()
    kanaly = session.query(Kanal).all()
    urls = [k.url for k in kanaly]
    session.close()

    lacznie_nowych = 0
    for url in urls:
        wynik = await fetch_feed(url)
        if not wynik:
            continue
        nowe = zapisz_kanal(wynik)
        for art in nowe:
            podsumowania = podsumuj_artykul(art["tytul"], art["opis"] or "")
            zapisz_podsumowanie(art["link"], podsumowania)
        lacznie_nowych += len(nowe)

    return {"sukces": True, "nowe_artykuly": lacznie_nowych}

@app.delete("/api/kanaly/{kanal_id}")
def usun_kanal(kanal_id: int):
    session = Session()
    kanal = session.query(Kanal).filter_by(id=kanal_id).first()
    if kanal:
        session.query(Artykul).filter_by(kanal_url=kanal.url).delete()
        session.delete(kanal)
        session.commit()
    session.close()
    return {"sukces": True}

@app.get("/api/trendy")
def get_trendy():
    from trend_analyzer import wykryj_trendy
    return wykryj_trendy()


@app.get("/api/kategorie")
def get_kategorie():
    return pobierz_kategorie()

@app.get("/api/artykuly/kategoria")
def get_artykuly_kategorii(kategoria: str):
    artykuly = pobierz_artykuly_kategorii(kategoria)
    return [{"id": a.id, "tytul": a.tytul, "link": a.link, "kanal_url": a.kanal_url,
             "data_publikacji": a.data_publikacji, "podsumowanie_krotkie": a.podsumowanie_krotkie,
             "sentyment": a.sentyment, "ulubiony": a.ulubiony, "kategoria": a.kategoria} for a in artykuly]

@app.post("/api/artykuly/{artykul_id}/kategoria")
def zmien_kategorie(artykul_id: int, dane: dict):
    from database import Session, Artykul
    session = Session()
    art = session.query(Artykul).filter_by(id=artykul_id).first()
    if art:
        art.kategoria = dane.get("kategoria", "INNE")
        session.commit()
    session.close()
    return {"sukces": True}
@app.post("/api/artykuly/{artykul_id}/ulubiony")
def toggle_ulubiony(artykul_id: int):
    stan = przelacz_ulubiony(artykul_id)
    return {"ulubiony": stan}

@app.get("/api/ulubione")
def get_ulubione():
    artykuly = pobierz_ulubione()
    return [{
        "id": a.id,
        "tytul": a.tytul,
        "link": a.link,
        "kanal_url": a.kanal_url,
        "data_publikacji": a.data_publikacji,
        "podsumowanie_krotkie": a.podsumowanie_krotkie,
        "sentyment": a.sentyment,
        "ulubiony": a.ulubiony,
    } for a in artykuly]

@app.get("/api/reader")
async def reader_view(url: str):
    import aiohttp
    from bs4 import BeautifulSoup
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        # usuń zbędne elementy
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "form"]):
            tag.decompose()
        # znajdź główną treść
        tresc = ""
        for selektor in ["article", "main", ".post-content", ".article-body", ".entry-content"]:
            el = soup.select_one(selektor)
            if el:
                tresc = el.get_text(separator="\n", strip=True)
                break
        if not tresc:
            tresc = soup.get_text(separator="\n", strip=True)[:3000]
        tytul = soup.title.string if soup.title else ""
        return {"tytul": tytul, "tresc": tresc[:5000]}
    except Exception as e:
        return {"tytul": "", "tresc": f"Nie udało się pobrać treści: {e}"}

# licznik nowych artykułów od ostatniego sprawdzenia
ostatnie_sprawdzenie = {"liczba": 0}

@app.get("/api/powiadomienia")
def get_powiadomienia():
    artykuly = pobierz_artykuly(50)
    nowe = ostatnie_sprawdzenie.get("liczba", 0)
    return {"nowe": nowe}

@app.post("/api/powiadomienia/reset")
def reset_powiadomienia():
    ostatnie_sprawdzenie["liczba"] = 0
    return {"sukces": True}

class ChatWiadomosc(BaseModel):
    pytanie: str

@app.post("/api/chat")
def chat(dane: ChatWiadomosc):
    from ai_summarizer import client
    
    # pobierz ostatnie 20 artykułów jako kontekst
    artykuly = pobierz_artykuly(20)
    kontekst = "\n\n".join([
        f"Tytuł: {a.tytul}\nPodsumowanie: {a.podsumowanie_krotkie or a.opis or ''}\nLink: {a.link}"
        for a in artykuly
    ])

    prompt = f"""Jesteś asystentem analizującym artykuły z czytnika RSS. 
Masz dostęp do następujących artykułów:

{kontekst}

Pytanie użytkownika: {dane.pytanie}

Odpowiedz po polsku, konkretnie i zwięźle. Jeśli pytanie dotyczy konkretnego artykułu, odwołaj się do niego."""

    odpowiedz = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return {"odpowiedz": odpowiedz.text}