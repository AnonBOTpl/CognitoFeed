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
            "ulubiony": art.ulubiony,
            "kategoria": art.kategoria or "INNE",
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
            "ulubiony": art.ulubiony,
            "kategoria": art.kategoria or "INNE",
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

@app.get("/api/kanaly/dodaj/progress")
async def dodaj_kanal_progress(url: str):
    from rss_parser import fetch_feed
    from ai_summarizer import podsumuj_artykul, przypisz_kategorie
    from fastapi.responses import StreamingResponse
    import json

    async def stream():
        def msg(dane: dict):
            return f"data: {json.dumps(dane, ensure_ascii=False)}\n\n"

        yield msg({"status": "fetch", "tekst": "Pobieram kanał...", "proc": 5})

        wynik = await fetch_feed(url)
        if not wynik:
            yield msg({"status": "error", "tekst": "Nie udało się pobrać kanału – sprawdź URL", "proc": 0})
            return

        yield msg({"status": "fetch", "tekst": f"Znaleziono: {wynik['tytuł']}", "proc": 15})

        nowe = zapisz_kanal(wynik)
        total = len(nowe)

        if total == 0:
            yield msg({"status": "done", "tekst": "Kanał już istnieje, brak nowych artykułów", "proc": 100})
            return

        yield msg({"status": "ai", "tekst": f"Przetwarzam {total} artykułów...", "proc": 20})

        for i, art in enumerate(nowe):
            proc = 20 + int((i / total) * 75)
            yield msg({"status": "ai", "tekst": f"AI analizuje: {art['tytul'][:50]}...", "proc": proc})
            podsumowania = podsumuj_artykul(art["tytul"], art["opis"] or "")
            zapisz_podsumowanie(art["link"], podsumowania)
            kategoria = przypisz_kategorie(art["tytul"], art["opis"] or "")
            zapisz_kategorie(art["link"], kategoria)

        yield msg({"status": "done", "tekst": f"✅ Dodano '{wynik['tytuł']}' – {total} artykułów", "proc": 100})

    return StreamingResponse(stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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
             "sentyment": a.sentyment, "ulubiony": a.ulubiony, "kategoria": a.kategoria or "INNE"} for a in artykuly]

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


@app.get("/api/wykryj-rss")
async def wykryj_rss(url: str):
    import aiohttp
    from bs4 import BeautifulSoup

    # normalizuj URL
    if not url.startswith("http"):
        url = "https://" + url
    # usuń trailing slash
    url = url.rstrip("/")

    znalezione = []
    sprawdzone = set()

    async def szukaj_w_stronie(adres: str):
        if adres in sprawdzone:
            return
        sprawdzone.add(adres)
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with aiohttp.ClientSession() as session:
                async with session.get(adres, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        return
                    html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            # szukaj tagów link z RSS/Atom
            for tag in soup.find_all("link", type=["application/rss+xml", "application/atom+xml"]):
                href = tag.get("href", "")
                if not href:
                    continue
                if href.startswith("/"):
                    href = url + href
                elif not href.startswith("http"):
                    href = url + "/" + href
                tytul = tag.get("title", href)
                if href not in [r["url"] for r in znalezione]:
                    znalezione.append({"tytul": tytul, "url": href})

            # szukaj też linków a href które zawierają rss/feed/atom
            if len(znalezione) == 0:
                for tag in soup.find_all("a", href=True):
                    href = tag["href"]
                    if any(x in href.lower() for x in ["rss", "feed", "atom", "xml"]):
                        if href.startswith("/"):
                            href = url + href
                        elif not href.startswith("http"):
                            href = url + "/" + href
                        tytul = tag.get_text(strip=True) or href
                        if href not in [r["url"] for r in znalezione]:
                            znalezione.append({"tytul": tytul, "url": href})
        except Exception:
            pass

    # sprawdź główną stronę
    await szukaj_w_stronie(url)

    # jeśli nic nie znaleziono – sprawdź popularne ścieżki
    if not znalezione:
        popularne = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml",
                     "/feeds/posts/default", "/feed/rss", "/rss/all.xml"]
        for sciezka in popularne:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(url + sciezka, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        ct = resp.headers.get("content-type", "")
                        if resp.status == 200 and any(x in ct for x in ["xml", "rss", "atom"]):
                            znalezione.append({"tytul": sciezka, "url": url + sciezka})
            except Exception:
                pass

    return {"znalezione": znalezione, "bazowy_url": url}

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


@app.get("/api/szukaj")
def szukaj(q: str, limit: int = 30):
    if not q or len(q) < 2:
        return []
    session = Session()
    wyniki = session.query(Artykul).filter(
        Artykul.tytul.ilike(f"%{q}%") |
        Artykul.opis.ilike(f"%{q}%") |
        Artykul.podsumowanie_krotkie.ilike(f"%{q}%")
    ).order_by(Artykul.dodano.desc()).limit(limit).all()
    session.close()
    return [{
        "id": a.id,
        "tytul": a.tytul,
        "link": a.link,
        "kanal_url": a.kanal_url,
        "data_publikacji": a.data_publikacji,
        "podsumowanie_krotkie": a.podsumowanie_krotkie,
        "sentyment": a.sentyment,
        "ulubiony": a.ulubiony,
        "kategoria": a.kategoria or "INNE",
    } for a in wyniki]