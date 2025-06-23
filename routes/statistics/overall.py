from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import Author, Article, Research, PublicationAuthor, ResearcherAuthor
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime

router = APIRouter(
    tags=['Overall Statistics']
)


@router.get("/stats/summary", response_model=StandardResponse)
def get_summary_counts(db: Session = Depends(get_db)):
    total_authors = db.query(Author).count()
    total_articles = db.query(Article).count()
    total_researches = db.query(Research).count()

    total_article_authors = db.query(PublicationAuthor.author_id).distinct().count()
    total_research_authors = db.query(ResearcherAuthor.author_id).distinct().count()

    return StandardResponse(
        success=True,
        message="Summary data fetched successfully",
        data={
            "total_authors": total_authors,
            "total_articles": total_articles,
            "total_researches": total_researches,
            "total_article_authors": total_article_authors,
            "total_research_authors": total_research_authors
        }
    )
