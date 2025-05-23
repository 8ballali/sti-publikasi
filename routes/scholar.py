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


router = APIRouter()

router = APIRouter(
    tags=['Google_Scholar']
)


@router.get("/scrape/scholar")
async def scrape_scholar(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scholar_scrapping(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scholar_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scholar selesai dan data telah disimpan ke database!"}

@router.post("/upload/google-scholar-excel")
async def upload_google_scholar_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        return {"error": "Format file harus Excel (.xls/.xlsx) atau CSV"}

    df = pd.read_excel(file.file) if file.filename.endswith(('.xls', '.xlsx')) else pd.read_csv(file.file)
    inserted_count = 0
    linked_count = 0

    for _, row in df.iterrows():
        title = str(row.get("Judul", "")).strip()
        year = str(row.get("Tahun", "")).strip()
        url = str(row.get("Paper Link", "")).strip()
        journal = str(row.get("Kategori Jurnal", "")).strip()
        cited = str(row.get("Cited", "")).strip()
        user_sinta_id = str(row.get("User ID", "")).strip()

        # Hapus "Authors : " lalu split berdasarkan koma
        authors_raw = str(row.get("Author", "")).replace("Authors :", "").strip()
        authors = [a.strip() for a in authors_raw.split(',') if a.strip() and "..." not in a]

        # Cek apakah artikel sudah ada berdasarkan judul + source
        existing_article = db.query(Article).filter_by(title=title, source="GOOGLE_SCHOLAR").first()
        if existing_article:
            article = existing_article
        else:
            article = Article(
                title=title,
                year=int(year) if year.isdigit() else None,
                article_url=url,
                journal=journal,
                citation_count=int(cited) if cited.isdigit() else None,
                source="GOOGLE_SCHOLAR"
            )
            db.add(article)
            db.commit()
            db.refresh(article)
            inserted_count += 1

        # Temukan author berdasarkan User ID → Author → User
        author = db.query(Author).filter(Author.sinta_id == user_sinta_id).first()
        if not author:
            continue

        user = db.query(User).filter(User.id == author.user_id).first()
        if not user or not user.name:
            continue

        # Gunakan pendekatan keyword untuk tentukan author_order
        lecturer_keywords = [kw for kw in user.name.lower().split() if len(kw) > 2]
        author_order = None

        for idx, name in enumerate(authors):
            if any(kw in name.lower() for kw in lecturer_keywords):
                author_order = idx + 1
                break

        if author_order is not None:
            existing_rel = db.query(PublicationAuthor).filter_by(
                article_id=article.id,
                author_id=author.id
            ).first()
            if not existing_rel:
                db.add(PublicationAuthor(
                    article_id=article.id,
                    author_id=author.id,
                    author_order=author_order
                ))
                db.commit()
                linked_count += 1

    return {
        "success": True,
        "inserted_articles": inserted_count,
        "linked_authors": linked_count
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


@router.get("/scrape/scholar/debug")
async def debug_scrape_google_scholar(db: Session = Depends(get_db)):
    lecturers = db.query(User.name, User.id, Author.sinta_profile_url)\
                  .join(Author)\
                  .all()

    headers = {'User-Agent': 'Mozilla/5.0'}
    all_results = []
    total_scraped = 0

    for lecturer_name, user_id, profile_link in lecturers:
        if not profile_link:
            continue

        scholar_url = f"{profile_link}?view=google_scholar"
        response = requests.get(scholar_url, headers=headers)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('div', class_='ar-list-item mb-5')

        for item in articles:
            title_tag = item.find('div', class_='ar-title').find('a')
            title = title_tag.text.strip() if title_tag else 'N/A'
            article_url = title_tag['href'] if title_tag and title_tag.has_attr('href') else 'N/A'

            author_names = []
            author_order = None
            meta_divs = item.find_all('div', class_='ar-meta')
            for div in meta_divs:
                tag = div.find('a', href='#!')
                if tag and "Authors :" in tag.text:
                    raw = tag.text.split("Authors :")[-1]
                    author_names = [a.strip() for a in raw.split(',') if a.strip() and "..." not in a]
                    lecturer_keys = lecturer_name.lower().split()
                    for idx, name in enumerate(author_names):
                        if any(key in name.lower() for key in lecturer_keys if len(key) > 2):
                            author_order = idx + 1
                            break
                    break

            journal_category = 'N/A'
            jc_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
            if jc_tag:
                journal_category = jc_tag.text.strip()

            year, cited = 'N/A', 'N/A'
            if len(meta_divs) > 1:
                for a_tag in meta_divs[1].find_all('a', href='#!'):
                    icon = a_tag.find('i')
                    if icon:
                        classes = icon.get('class', [])
                        if 'zmdi-calendar' in classes:
                            year = a_tag.text.replace('📅', '').strip()
                        elif 'zmdi-comment-list' in classes:
                            cited = a_tag.text.replace('🔗', '').strip()

            all_results.append({
                "lecturer": lecturer_name,
                "title": title,
                "article_url": article_url,
                "authors": author_names,
                "journal_category": journal_category,
                "year": year,
                "citation_count": cited,
                "author_order": author_order
            })
            total_scraped += 1

    return {
        "total_articles_scraped": total_scraped,
        "results": all_results
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
