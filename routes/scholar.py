from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO
from difflib import get_close_matches
from database import get_db
from models import User, Author, Article, PublicationAuthor
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync
from bs4 import BeautifulSoup
import requests, re
import unicodedata
from schemas import ArticleResponse
from typing import List
from sqlalchemy import and_


router = APIRouter()

router = APIRouter(
    tags=['Google_Scholar']
)


def generate_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) < 2:
        return name  # fallback
    initials = ''.join([p[0].upper() for p in parts[:-1]])
    last_name = parts[-1].capitalize()
    return f"{initials} {last_name}"


@router.get("/sync/scholar")
async def sync_scholar(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scholar_sync(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scholar_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Sync Data Article Google Scholar Selesai"}





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

@router.post("/google-scholar/upload/all-in-one")
async def upload_google_scholar_single_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        return {"error": "Format file harus Excel (.xls/.xlsx) atau CSV"}

    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {str(e)}")

    inserted_count = 0
    skipped_count = 0
    already_exist = 0

    for _, row in df.iterrows():
        user_id = str(row.get("User ID", "")).strip()
        title = str(row.get("Judul", "")).strip()
        publisher_link = str(row.get("Publisher Link", "")).strip()
        paper_link = str(row.get("Paper Link", "")).strip()
        url = publisher_link if publisher_link else paper_link
        journal = str(row.get("Kategori Jurnal", "")).strip()
        year = str(row.get("Tahun", "")).strip()
        cited = str(row.get("Cited", "")).strip()
        authors_raw = str(row.get("Author", "")).replace("Authors :", "").strip()
        abstract = str(row.get("Abstract", "")).strip() if "Abstract" in df.columns else None
        doi = str(row.get("DOI", "")).strip() if "DOI" in df.columns else None

        # Cari Author
        authors_list = [a.strip() for a in authors_raw.split(',') if a.strip() and "..." not in a]
        author = db.query(Author).filter(Author.sinta_id == user_id).first()
        if not author or not author.user:
            skipped_count += 1
            continue

        user = author.user
        expected_initial = generate_initials(user.name)

        author_order = None
        for idx, name in enumerate(authors_list):
            if name.lower() == expected_initial.lower():
                author_order = idx + 1
                break

        if author_order is None:
            lecturer_keywords = [kw for kw in user.name.lower().split() if len(kw) > 2]
            for idx, name in enumerate(authors_list):
                if any(kw in name.lower() for kw in lecturer_keywords):
                    author_order = idx + 1
                    break

        if author_order is None:
            skipped_count += 1
            continue

        # Cek duplikat berdasarkan judul + source
        existing = db.query(Article).filter(and_(
            Article.title == title,
            Article.source == "GOOGLE_SCHOLAR"
        )).first()
        if existing:
            already_exist += 1
            continue

        # Tambahkan artikel baru
        article = Article(
            title=title,
            year=int(year) if year.isdigit() else None,
            article_url=url,
            journal=journal,
            source="GOOGLE_SCHOLAR",
            citation_count=int(cited) if cited.isdigit() else None,
            abstract=abstract if abstract else None,
            doi=doi if doi else None
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # Tambahkan relasi penulis
        db.add(PublicationAuthor(
            article_id=article.id,
            author_id=author.id,
            author_order=author_order
        ))
        db.commit()

        inserted_count += 1

    return {
        "success": True,
        "inserted_articles": inserted_count,
        "skipped_rows": skipped_count,
        "duplicates_skipped": already_exist
    }
