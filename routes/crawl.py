from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data
from models import User, Author
from schemas import PaperResponse
from typing import List
from repository.garuda_abstract_crawl import scrape_garuda_data 

router = APIRouter()

router = APIRouter(
    tags=['CRAWL']
)

@router.get("/scrape/authors", status_code=status.HTTP_200_OK)
async def scrape_authors(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping selesai dan data telah disimpan ke database!"}

@router.get("/scrape/garuda", response_model=List[PaperResponse])
async def scrape_garuda_route(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen (nama + profil Sinta) dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).join(Author, User.id == Author.user_id).all()

    for lecturer_name, profile_link in lecturers:
        if profile_link:  # Pastikan profil Sinta tersedia
            results.extend(scrape_garuda_data(lecturer_name, profile_link))

    return results


