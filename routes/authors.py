from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, scrape_and_save_authors
from models import User, Author, Subject, UserSubject
from repository.subject_crawl import scrape_all_subjects


router = APIRouter()

router = APIRouter(
    tags=['Authors']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):

    result = scrape_and_save_authors(db)
    return result

@router.get("/scrape/subjects")
async def scrape_subjects(db: Session = Depends(get_db)):
    return scrape_all_subjects(db)
