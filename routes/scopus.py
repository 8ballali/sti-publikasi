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


@router.get("/scrape/scopus")
async def scrape_scopus(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scopus_scrapping(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scopus_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scopus selesai dan data telah disimpan ke database!"}


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

@router.post("/upload/scopus-excel")
async def upload_scopus_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        return {"error": "Format file harus Excel (.xls/.xlsx) atau CSV"}

    df = pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
    inserted_count = 0

    for _, row in df.iterrows():
        sinta_id = str(row.get("User ID", "")).strip()
        title = str(row.get("Title", "")).strip()
        accred = str(row.get("Accred", "")).strip()
        journal = str(row.get("Jurnal", "")).strip()
        year = str(row.get("Year", "")).strip()
        cited = row.get("Cited", None)
        author_order = row.get("Order", None)

        # Validasi dasar
        if not title or not sinta_id:
            continue

        # Cek author by sinta_id
        author = db.query(Author).filter(Author.sinta_id == sinta_id).first()
        if not author:
            continue

        # Cek duplikat berdasarkan title + source
        existing_article = db.query(Article).filter(and_(
            Article.title == title,
            Article.source == "SCOPUS"
        )).first()

        if existing_article:
            continue

        article = Article(
            title=title,
            year=int(year) if year.isdigit() else None,
            accred=accred,
            journal=journal,
            source="SCOPUS",
            citation_count=int(cited) if pd.notna(cited) and str(cited).isdigit() else None
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # Tambahkan hubungan ke publication_authors
        pub_author = PublicationAuthor(
            article_id=article.id,
            author_id=author.id,
            author_order=int(author_order) if pd.notna(author_order) and str(author_order).isdigit() else None
        )
        db.add(pub_author)
        db.commit()
        inserted_count += 1

    return {
        "success": True,
        "message": f"{inserted_count} artikel berhasil dimasukkan dari file Scopus.",
    }




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

@router.post("/scopus/upload-abstracts")
async def upload_abstracts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        csv_buffer = StringIO(contents.decode('utf-8'))
        df = pd.read_csv(csv_buffer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

    if df.shape[1] < 4:
        raise HTTPException(status_code=400, detail="CSV file must have at least 9 columns.")

    updated_count = 0
    unmatched_titles = []

    # Ambil hanya artikel dari source SCOPUS
    all_articles = db.query(Article).filter(Article.source == "SCOPUS").all()
    normalized_db_titles = {normalize(article.title): article for article in all_articles}

    for index, row in df.iterrows():
        csv_title_raw = str(row.iloc[0]).strip()        # kolom ke-2: judul
        raw_article_url = row.iloc[7]
        new_article_url = str(raw_article_url).strip() if not pd.isna(raw_article_url) else ""
        raw_abstract = row.iloc[1]
        new_abstract = str(raw_abstract).strip() if not pd.isna(raw_abstract) else ""


        normalized_csv_title = normalize(csv_title_raw)
        match = get_close_matches(normalized_csv_title, normalized_db_titles.keys(), n=1, cutoff=0.8)

        if match:
            matched_article = normalized_db_titles[match[0]]
            matched_article.abstract = new_abstract

            if new_article_url:  #Updating Abstract
                matched_article.article_url = new_article_url

            updated_count += 1
        else:
            unmatched_titles.append(csv_title_raw)

    db.commit()

    return {
        "message": f"{updated_count} articles updated successfully.",
        "unmatched_titles": unmatched_titles
    }

