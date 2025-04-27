from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from repository.garuda_abstract_crawl import garuda_data,garuda_scrapping, garuda_sync, garuda_abstract_scraping
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from bs4 import BeautifulSoup
import requests, time
import re

from models import User, Author, Article, Subject, UserSubject
from schemas import GarudaAbstractResponse


router = APIRouter()

router = APIRouter(
    tags=['Garuda']
)

@router.get("/scrape/garuda")
async def scrape_garuda(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            
            
            scraped_data = garuda_scrapping(lecturer_name, profile_link)
            
            print(f"Scraped data untuk {lecturer_name}: {scraped_data}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")  # Debugging
            
            # Simpan hasil scraping ke database
            garuda_data(scraped_data, db)  

            results.extend(scraped_data)

    return {"message": "Scraping selesai dan data telah disimpan ke database!"}

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

    return {"message": "Sync Data selesai, Data Telah Diperbarui!"}


@router.get("/scrape/abstract/garuda/debug")
async def scrape_abstract_garuda_debug(db: Session = Depends(get_db)):
    # Ambil hanya artikel dari GARUDA yang abstract-nya masih kosong
    articles = db.query(Article).filter(
        Article.source == "GARUDA",
        Article.abstract == None
    ).all()

    print(f"📄 Total artikel GARUDA tanpa abstract: {len(articles)}")

    results = []

    for idx, article in enumerate(articles, start=1):
        title = article.title
        url = article.article_url
        abstract_text = "N/A"

        print(f"\n[{idx}/{len(articles)}] 🔍 Memproses: {title}")
        print(f"🌐 URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            abstract_div = soup.find("div", class_="abstract-article")

            if abstract_div:
                abstract_xmp = abstract_div.find("xmp", class_="abstract-article")
                abstract_text = abstract_xmp.text.strip() if abstract_xmp else "N/A"
                print(f"✅ Abstract ditemukan: {abstract_text[:50]}...")
            else:
                print("⚠️ Tidak menemukan div.abstract-article")

        except Exception as e:
            abstract_text = f"❌ Error: {str(e)}"
            print(f"❌ Gagal scraping: {str(e)}")

        results.append({
            "title": title,
            "article_url": url,
            "abstract": abstract_text
        })

        time.sleep(1)  # Biar nggak diblokir

    return {"scraped_abstracts": results}

@router.get("/scrape/garuda/debug")
async def garuda_debug(db: Session = Depends(get_db)):
    results = []

    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen ditemukan: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"\n📚 Memproses (GARUDA): {lecturer_name}")
            garuda_url = f"{profile_link}?view=garuda"
            print(f"🔗 Fetching from: {garuda_url}")
            response = requests.get(garuda_url)

            if response.status_code != 200:
                print(f"❌ Gagal mengambil data dari {garuda_url}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('div', class_='ar-list-item mb-5')

            for item in articles:
                title_tag = item.find('div', class_='ar-title').find('a')
                title = title_tag.text.strip() if title_tag else 'N/A'
                publication_link = title_tag['href'] if title_tag and title_tag.has_attr('href') else 'N/A'
                
                journal_category_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
                journal_category = journal_category_tag.text.strip() if journal_category_tag else 'N/A'

                second_meta_div = item.find_all('div', class_='ar-meta')[1] if len(item.find_all('div', class_='ar-meta')) > 1 else None
                author_order, year, doi, accred = 'N/A', 'N/A', 'N/A', 'N/A'
                authors = []

                if second_meta_div:
                    for a_tag in second_meta_div.find_all('a', href='#!'):
                        text = a_tag.text.strip()
                        if 'Author Order' in text:
                            match = re.search(r'\d+', text)
                            if match:
                                author_order = match.group()
                        else:
                            i_tag = a_tag.find('i')
                            if i_tag:
                                icon_class = i_tag.get('class', [])
                                if 'zmdi-calendar' in icon_class:
                                    year = text.replace('📅', '').strip()
                                elif 'zmdi-comment-list' in icon_class:
                                    doi = text.replace('🔗', '').replace('DOI: ', '').strip()
                                elif 'zmdi-chart-donut' in icon_class:
                                    accred = text.replace('📊', '').replace('Accred : ', '').strip()
                            else:
                                authors.append(text)

                results.append({
                    "lecturer_name": lecturer_name,
                    "title": title,
                    "publication_link": publication_link,
                    "journal_category": journal_category,
                    "authors": authors,
                    "author_order": author_order,
                    "year": year,
                    "doi": doi,
                    "accred": accred
                })

    return {"scraped_results": results}