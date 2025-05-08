from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data
from models import User, Author, Subject, UserSubject
from repository.subject_crawl import scrape_all_subjects


router = APIRouter()

router = APIRouter(
    tags=['Authors']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping Authors selesai dan data telah disimpan ke database!"}


@router.get("/scrape/subjects")
async def scrape_subjects(db: Session = Depends(get_db)):
    return scrape_all_subjects(db)


@router.get("/scrape/authors/debug")
async def scrape_authors_debug():
    scraped_data = scrape_sinta()

    # Ubah hasil scraping ke bentuk dictionary agar bisa dikembalikan dalam JSON
    debug_results = []
    for data in scraped_data:
        debug_results.append({
            "lecturer_name": data.lecturer_name,
            "sinta_profile_url": data.sinta_profile_url,
            "sinta_id": data.sinta_id,
            "scopus_hindex": data.scopus_hindex,
            "gs_hindex": data.gs_hindex,
            "profile_link": data.profile_link,
            "sinta_score_3yr": data.sinta_score_3yr,
            "sinta_score_total": data.sinta_score_total,
            "affil_score_3yr": data.affil_score_3yr,
            "affil_score_total": data.affil_score_total
        })

    return {"scraped_results": debug_results}