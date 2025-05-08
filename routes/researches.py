from fastapi import APIRouter,  Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author, ResearcherAuthor, Research
from bs4 import BeautifulSoup
import requests, time
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync
from repository.research_crawl import scrape_sinta_research
import re



router = APIRouter()

router = APIRouter(
    tags=['Researches']
)

@router.get("/scrape/research/sinta/debug")
async def scrape_research_sinta_debug(db: Session = Depends(get_db)):
    results = scrape_sinta_research(db)
    return {"scraped_researches": results}