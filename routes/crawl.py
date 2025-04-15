from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data
from models import User, Author
from schemas import PaperResponse
from typing import List
from repository.garuda_abstract_crawl import garuda_data,garuda_scrapping, garuda_sync
from fastapi.encoders import jsonable_encoder
from bs4 import BeautifulSoup
import requests

router = APIRouter()

router = APIRouter(
    tags=['CRAWL']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping Authors selesai dan data telah disimpan ke database!"}

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


@router.get("/scrape/scholar/debug")
async def scrape_scholar_debug(db: Session = Depends(get_db)):
    results = []

    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen ditemukan: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"\n📚 Memproses: {lecturer_name}")
            google_scholar_url = f"{profile_link}?view=google_scholar"
            response = requests.get(google_scholar_url)

            if response.status_code != 200:
                print(f"Gagal mengambil data dari {google_scholar_url}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('div', class_='ar-list-item mb-5')

            for item in articles:
                title_tag = item.find('div', class_='ar-title')
                link_tag = title_tag.find('a') if title_tag else None
                title = link_tag.text.strip() if link_tag else 'N/A'
                publication_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else 'N/A'

                authors = []
                author_order = "N/A"
                meta_divs = item.find_all('div', class_='ar-meta')

                for div in meta_divs:
                    author_tag = div.find('a', href='#!')
                    if author_tag and "Authors :" in author_tag.text:
                        author_text = author_tag.text.strip()
                        authors_part = author_text.split("Authors :")[-1]
                        authors = [a.strip() for a in authors_part.split(',') if a.strip() and "..." not in a]
                        
                        # Normalisasi nama dosen → ambil nama belakang (atau nama unik)
                        lecturer_keywords = lecturer_name.lower().split()
                        for idx, name in enumerate(authors):
                            if any(key in name.lower() for key in lecturer_keywords if len(key) > 2):
                                author_order = str(idx + 1)
                                break
                        break  # selesai kalau sudah nemu authors

                results.append({
                    "lecturer_name": lecturer_name,
                    "title": title,
                    "publication_link": publication_link,
                    "authors": authors,
                    "author_order": author_order
                })

    return {"scraped_results": results}
