from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, scrape_and_save_authors, get_top_authors
from models import User, Author, Subject, UserSubject
from repository.subject_crawl import scrape_all_subjects
from schemas import TopAuthorResponse


router = APIRouter()

router = APIRouter(
    tags=['Authors & Subjects']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):

    result = scrape_and_save_authors(db)
    return result

@router.get("/scrape/subjects")
async def scrape_subjects(db: Session = Depends(get_db)):
    return scrape_all_subjects(db)

@router.get("/authors/top")
def top_authors(limit: int = 10, db: Session = Depends(get_db)):
    return get_top_authors(db, limit)
