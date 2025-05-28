from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from repository.garuda_abstract_crawl import garuda_data,garuda_scrapping, garuda_sync, garuda_abstract_scraping
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from bs4 import BeautifulSoup
import requests, time
import re
from repository.garuda_abstract_crawl import get_lecturers_with_profiles, save_scraped_data_to_db
from models import User, Author, Article, PublicationAuthor
from schemas import GarudaAbstractResponse
import io
import pandas as pd
from sqlalchemy import or_, and_



router = APIRouter()

router = APIRouter(
    tags=['Garuda']
)

@router.get("/scrape/garuda")
async def scrape_garuda_route(db: Session = Depends(get_db)):
    lecturers = get_lecturers_with_profiles(db)
    all_results = []

    for lecturer_name, profile_link in lecturers:
        if not profile_link:
            continue
        print(f"Scraping data for: {lecturer_name}")
        scraped_papers = garuda_scrapping(lecturer_name, profile_link)
        print(f"Scraped {len(scraped_papers)} papers for {lecturer_name}")
        save_scraped_data_to_db(scraped_papers, db)
        all_results.extend(scraped_papers)

    return {
        "success": True,
        "message": "Scraping Garuda Success",
        "total_scraped": len(all_results),
        "scraped_results": all_results
    }

@router.post("/upload/garuda")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validasi format file
    if not file.filename.endswith(('.csv',)):
        return {"error": "Format file harus CSV (.csv)"}

    # Load DataFrame
    df = pd.read_csv(file.file)

    inserted_articles = 0
    inserted_relations = 0

    for _, row in df.iterrows():
        title = str(row.get("Judul", "")).strip()
        year = str(row.get("Tahun", "")).strip()
        doi = str(row.get("DOI", "")).replace("DOI:", "").strip()
        url = str(row.get("Paper Link", "")).strip()
        journal = str(row.get("Kategori Jurnal", "")).strip()
        index_jurnal = str(row.get("Index Jurnal", "")).strip()
        university = str(row.get("Universitas", "")).strip()
        sinta_id_excel = str(row.get("User ID", "")).strip()
        author_order = str(row.get("Order", "")).strip()

        # Bersihkan Accred
        accred = index_jurnal.replace("Accred :", "", 1).strip() if index_jurnal.lower().startswith("accred") else index_jurnal


        # Cek keberadaan artikel
        article = db.query(Article).filter(
            or_(Article.doi == doi, Article.title == title)
        ).first()

        if not article:
            article = Article(
                title=title,
                year=int(year) if year.isdigit() else None,
                doi=doi if doi and doi.lower() != "none" else None,
                article_url=url,
                accred=accred,
                journal=journal,
                source="GARUDA",
                university=university
            )
            db.add(article)
            db.commit()
            db.refresh(article)
            inserted_articles += 1

        # Dapatkan Author dari User ID (sinta_id)
        author = db.query(Author).filter(Author.sinta_id == sinta_id_excel).first()
        if not author:
            continue  # Skip jika author tidak ditemukan

        # Cek duplikat relasi
        existing_rel = db.query(PublicationAuthor).filter_by(
            article_id=article.id,
            author_id=author.id
        ).first()

        if not existing_rel:
            # Tambahkan relasi dengan author_order
            
            relation = PublicationAuthor(
                article_id=article.id,
                author_id=author.id,
                author_order=int(author_order)
            )
            db.add(relation)
            db.commit()
            inserted_relations += 1

    return {
        "success": True,
        "message": "Excel berhasil diproses.",
        "inserted_articles": inserted_articles,
        "inserted_publication_authors": inserted_relations
    }

@router.get("/scrape/abstract/garuda")
async def abstract_garuda(db: Session = Depends(get_db)):
    results = []

    articles = db.query(Article.id, Article.title, Article.article_url).filter(
        Article.source == "GARUDA",
        Article.abstract == None
    ).all()

    print(f"🔍 Jumlah artikel GARUDA tanpa abstract: {len(articles)}")

    scraped_data: List[GarudaAbstractResponse] = garuda_abstract_scraping(articles)

    print(f"💾 Mulai menyimpan {len(scraped_data)} abstract ke database...")

    for data in scraped_data:
        try:
            article = db.query(Article).filter_by(id=data.article_id).first()
            if article:
                article.abstract = data.abstract
                db.add(article)
                db.commit()
                results.append({
                    "id": article.id,
                    "title": article.title,
                    "abstract": article.abstract
                })
        except SQLAlchemyError as e:
            db.rollback()
            print(f"❌ Gagal simpan ID {data.article_id}: {str(e)}")

    return {
        "message": "Scraping GARUDA selesai dan abstract disimpan ke database!",
        "total_saved": len(results),
        "saved_data": results
    }

@router.get("/sync/garuda")
async def sync_garuda(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            
            # 🔹 Pastikan memanggil `scrape_garuda_data()` dengan argumen yang benar
            scraped_data = garuda_sync(lecturer_name, profile_link)
            
            print(f"Scraped data untuk {lecturer_name}: {scraped_data}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")  # Debugging
            
            # Simpan hasil scraping ke database
            garuda_data(scraped_data, db)  

            results.extend(scraped_data)

    return {
        "message": "Sync GARUDA selesai",
        "total_saved": len(results),
        "saved_data": results
    }




