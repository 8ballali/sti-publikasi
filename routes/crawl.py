from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data

router = APIRouter()

router = APIRouter(
    tags=['CRAWL']
)

@router.get("/scrape")
async def scrape_and_store(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping selesai dan data telah disimpan ke database!"}


