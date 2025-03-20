from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data

from models import User, Author
from schemas import PaperResponse
from typing import List
from repository.garuda_abstract_crawl import garuda_data,garuda_scrapping 
from fastapi.encoders import jsonable_encoder

router = APIRouter()

router = APIRouter(
    tags=['CRAWL']
)

@router.get("/scrape")
async def scrape_and_store(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping selesai dan data telah disimpan ke database!"}

@router.get("/scrape/garuda")
async def scrape_and_store_garuda(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            
            # 🔹 Pastikan memanggil `scrape_garuda_data()` dengan argumen yang benar
            scraped_data = garuda_scrapping(lecturer_name, profile_link)
            
            print(f"Scraped data untuk {lecturer_name}: {scraped_data}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")  # Debugging
            
            # Simpan hasil scraping ke database
            garuda_data(scraped_data, db)  

            results.extend(scraped_data)

    return {"message": "Scraping selesai dan data telah disimpan ke database!"}


@router.get("/test/scrape/garuda", response_model=List[PaperResponse])
async def scrape_garuda_route(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Lecturers data: {lecturers}")  # Cek apakah ada data tambahan yang tidak diharapkan


    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            scraped_data_garuda = scrape_garuda_data(lecturer_name, profile_link)  # Scraping
            print(f"Scraped data untuk {lecturer_name}: {scraped_data_garuda}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data_garuda)}")  # Debugging
            # save_scraped_data(scraped_data_garuda, db)  # Simpan hasil scraping ke database
            results.extend(scraped_data_garuda)

    return results

@router.get("/scrape/test")
async def scrape_garuda_route(db: Session = Depends(get_db)):
    lectures = db.query(User.id,User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    
    # Konversi hasil query menjadi list of dictionaries
    result = [{"id": user_id, "name": name, "sinta_profile_url": url} for user_id, name, url in lectures]
    
    return jsonable_encoder(result)