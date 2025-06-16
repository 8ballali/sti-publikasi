from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author, Article
from repository.scopus_abstract_crawl import scopus_scrapping,scopus_data, scopus_sync
import pandas as pd
from io import StringIO
from difflib import get_close_matches
import requests,time
import re, random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import unicodedata
from selenium.webdriver.support import expected_conditions as EC
from models import PublicationAuthor
from sqlalchemy import and_



router = APIRouter()

router = APIRouter(
    tags=['Scopus']
)

@router.get("/sync/scopus")
async def sync_scopus(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scopus_sync(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scopus_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scopus selesai dan data telah disimpan ke database!"}



def normalize(text: str) -> str:
    # Ubah ke huruf kecil
    text = text.lower()

    # Hilangkan accent/diakritik (contoh: é -> e)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')

    # Hilangkan karakter non-alfabet dan angka (kecuali spasi)
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # Hilangkan spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    return text

@router.post("/upload/scopus-excel")
async def upload_scopus_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        return {"error": "Format file harus Excel (.xls/.xlsx) atau CSV"}

    df = pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
    inserted_articles = 0
    inserted_relations = 0
    skipped_relations = 0

    for _, row in df.iterrows():
        sinta_id = str(row.get("User ID", "")).strip()
        title = str(row.get("Title", "")).strip()
        accred = str(row.get("Accred", "")).strip()
        journal = str(row.get("Jurnal", "")).strip()
        year = str(row.get("Year", "")).strip()
        cited = row.get("Cited", None)
        author_order = row.get("Order", None)
        abstract = str(row.get("Abstract", "")).strip()
        article_url = str(row.get("Publisher Link", "")).strip()
        doi = str(row.get("DOI", "")).strip()

        # Validasi
        if not title or not sinta_id:
            continue

        # Cari author
        author = db.query(Author).filter(Author.sinta_id == sinta_id).first()
        if not author:
            continue

        # Cek apakah artikel sudah ada berdasarkan title + source
        article = db.query(Article).filter(
            and_(Article.title == title, Article.source == "SCOPUS")
        ).first()

        if not article:
            # Artikel belum ada → simpan
            article = Article(
                title=title,
                year=int(year) if year.isdigit() else None,
                accred=accred,
                journal=journal,
                source="SCOPUS",
                citation_count=int(cited) if pd.notna(cited) and str(cited).isdigit() else None,
                abstract=abstract,
                article_url=article_url,
                doi=doi
            )
            db.add(article)
            db.commit()
            db.refresh(article)
            inserted_articles += 1

        # Cek apakah relasi author-article sudah ada
        existing_relation = db.query(PublicationAuthor).filter_by(
            article_id=article.id,
            author_id=author.id
        ).first()

        if not existing_relation:
            # Simpan relasi baru
            pub_author = PublicationAuthor(
                article_id=article.id,
                author_id=author.id,
                author_order=int(author_order) if pd.notna(author_order) and str(author_order).isdigit() else None
            )
            db.add(pub_author)
            db.commit()
            inserted_relations += 1
        else:
            skipped_relations += 1

    return {
        "success": True,
        "inserted_articles": inserted_articles,
        "inserted_relations": inserted_relations,
        "skipped_relations": skipped_relations,
        "message": f"{inserted_articles} artikel baru ditambahkan, {inserted_relations} relasi author-artikel baru dimasukkan."
    }

