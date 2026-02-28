from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Kanal(Base):
    __tablename__ = "kanaly"
    id = Column(Integer, primary_key=True)
    tytul = Column(String(500))
    url = Column(String(1000), unique=True)
    opis = Column(Text)
    dodano = Column(DateTime, default=datetime.now)

class Artykul(Base):
    __tablename__ = "artykuly"
    id = Column(Integer, primary_key=True)
    kanal_url = Column(String(1000))
    tytul = Column(String(500))
    link = Column(String(1000), unique=True)
    opis = Column(Text)
    data_publikacji = Column(String(200))
    dodano = Column(DateTime, default=datetime.now)
    podsumowanie_krotkie = Column(Text, nullable=True)
    podsumowanie_srednie = Column(Text, nullable=True)
    sentyment = Column(String(200), nullable=True)
    ulubiony = Column(Boolean, default=False)

engine = create_engine("sqlite:///cognitofeed.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def zapisz_kanal(dane: dict):
    session = Session()
    istniejacy = session.query(Kanal).filter_by(url=dane["url"]).first()
    if not istniejacy:
        kanal = Kanal(tytul=dane["tytuł"], url=dane["url"], opis=dane["opis"])
        session.add(kanal)

    nowe = 0
    nowe_artykuly = []
    for art in dane["artykuły"]:
        istniejacy_art = session.query(Artykul).filter_by(link=art["link"]).first()
        if not istniejacy_art:
            artykul = Artykul(
                kanal_url=dane["url"],
                tytul=art["tytuł"],
                link=art["link"],
                opis=art["opis"],
                data_publikacji=art["data"]
            )
            session.add(artykul)
            nowe += 1
            nowe_artykuly.append({
                "tytul": art["tytuł"],
                "link": art["link"],
                "opis": art["opis"]
            })

    session.commit()
    session.close()
    print(f"Zapisano {nowe} nowych artykułów")
    return nowe_artykuly

def zapisz_podsumowanie(link: str, podsumowania: dict):
    session = Session()
    artykul = session.query(Artykul).filter_by(link=link).first()
    if artykul:
        artykul.podsumowanie_krotkie = podsumowania.get("krotkie")
        artykul.podsumowanie_srednie = podsumowania.get("srednie")
        artykul.sentyment = podsumowania.get("sentyment")
        session.commit()
    session.close()

def pobierz_artykuly(limit: int = 20) -> list:
    session = Session()
    artykuly = session.query(Artykul).order_by(Artykul.dodano.desc()).limit(limit).all()
    session.close()
    return artykuly

def przelacz_ulubiony(artykul_id: int) -> bool:
    session = Session()
    artykul = session.query(Artykul).filter_by(id=artykul_id).first()
    if artykul:
        artykul.ulubiony = not artykul.ulubiony
        session.commit()
        stan = artykul.ulubiony
        session.close()
        return stan
    session.close()
    return False

def pobierz_ulubione() -> list:
    session = Session()
    artykuly = session.query(Artykul).filter_by(ulubiony=True).order_by(Artykul.dodano.desc()).all()
    session.close()
    return artykuly