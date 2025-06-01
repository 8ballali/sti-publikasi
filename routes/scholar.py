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

@router.post("/upload/google-scholar")
async def upload_google_scholar(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        return {"error": "Format file harus Excel (.xls/.xlsx) atau CSV"}

    df = pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
    inserted_count = 0
    skipped_count = 0

    for _, row in df.iterrows():
        user_id = str(row.get("User ID", "")).strip()
        title = str(row.get("Judul", "")).strip()
        url = str(row.get("Paper Link", "")).strip()
        journal = str(row.get("Kategori Jurnal", "")).strip()
        year = str(row.get("Tahun", "")).strip()
        cited = str(row.get("Cited", "")).strip()
        authors_raw = str(row.get("Author", "")).replace("Authors :", "").strip()

        # Ambil Author
        authors_list = [a.strip() for a in authors_raw.split(',') if a.strip() and "..." not in a]

        # Cari author berdasarkan User ID ke tabel authors
        author = db.query(Author).filter(Author.sinta_id == user_id).first()
        if not author:
            skipped_count += 1
            continue

        user = author.user
        if not user:
            skipped_count += 1
            continue

        # Buat inisial nama dosen: "Christy Atika Sari" → "CA Sari"
        expected_initial = generate_initials(user.name)

        # Cari author_order yang cocok berdasarkan inisial
        author_order = None
        for idx, name in enumerate(authors_list):
            if name.lower() == expected_initial.lower():
                author_order = idx + 1
                break

        # Jika gagal pakai inisial, fallback ke keyword match
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
            continue

        # Simpan Article
        article = Article(
            title=title,
            year=int(year) if year.isdigit() else None,
            article_url=url,
            journal=journal,
            source="GOOGLE_SCHOLAR",
            citation_count=int(cited) if cited.isdigit() else None
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # Simpan relasi author → artikel
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
        "skipped_rows": skipped_count
    }


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

@router.post("/scholar/upload-abstracts")
async def upload_abstracts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        csv_buffer = StringIO(contents.decode('utf-8'))
        df = pd.read_csv(csv_buffer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

    if df.shape[1] < 9:
        raise HTTPException(status_code=400, detail="CSV file must have at least 9 columns.")

    updated_count = 0
    unmatched_titles = []

    # Ambil hanya artikel dari source GOOGLE_SCHOLAR
    all_articles = db.query(Article).filter(Article.source == "GOOGLE_SCHOLAR").all()
    normalized_db_titles = {normalize(article.title): article for article in all_articles}

    for index, row in df.iterrows():
        csv_title_raw = str(row.iloc[1]).strip()        # kolom ke-2: judul
        raw_article_url = row.iloc[7]
        new_article_url = str(raw_article_url).strip() if not pd.isna(raw_article_url) else ""
        raw_abstract = row.iloc[8]
        new_abstract = str(raw_abstract).strip() if not pd.isna(raw_abstract) else ""


        normalized_csv_title = normalize(csv_title_raw)
        match = get_close_matches(normalized_csv_title, normalized_db_titles.keys(), n=1, cutoff=0.8)

        if match:
            matched_article = normalized_db_titles[match[0]]
            matched_article.abstract = new_abstract

            if new_article_url:  # hanya update jika kolom 7 tidak kosong
                matched_article.article_url = new_article_url

            updated_count += 1
        else:
            unmatched_titles.append(csv_title_raw)

    db.commit()

    return {
        "message": f"{updated_count} articles updated successfully.",
        "unmatched_titles": unmatched_titles
    }



@router.get("/authors/{author_id}/articles", response_model=List[ArticleResponse])
def get_articles_by_author(author_id: int, db: Session = Depends(get_db)):
    publication_entries = db.query(PublicationAuthor).filter_by(author_id=author_id).all()

    articles = []
    for entry in publication_entries:
        article = entry.article
        if article:
            articles.append(ArticleResponse(
                id=article.id,
                title=article.title,
                year=article.year,
                article_url=article.article_url,
                journal=article.journal,
                source=article.source,
                author_order=entry.author_order
            ))
    return articles
