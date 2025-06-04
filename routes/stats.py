from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import Author, Article, Research
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime

router = APIRouter()
router = APIRouter(
    tags=['Statistics']
)


@router.get("/stats/summary", response_model=StandardResponse)
def get_summary_counts(db: Session = Depends(get_db)):
    total_authors = db.query(Author).count()
    total_articles = db.query(Article).count()
    total_researches = db.query(Research).count()

    return StandardResponse(
        success=True,
        message="Summary data fetched successfully",
        data={
            "total_authors": total_authors,
            "total_articles": total_articles,
            "total_researches": total_researches
        }
    )


@router.get("/statistics/chart", response_model=StandardResponse)
def get_statistics_chart(
    year_range: int = Query(3, ge=1, le=50, description="Year range: 3, 6, or 10"),
    db: Session = Depends(get_db)
):
    current_year = datetime.now().year
    start_year = current_year - year_range + 1

    # Ambil jumlah artikel per tahun
    article_counts = dict(
        db.query(Article.year, func.count(Article.id))
        .filter(Article.year >= start_year)
        .group_by(Article.year)
        .all()
    )

    # Ambil jumlah riset per tahun
    research_counts = dict(
        db.query(Research.year, func.count(Research.id))
        .filter(Research.year >= start_year)
        .group_by(Research.year)
        .all()
    )

    # Susun data untuk tiap tahun dalam rentang
    chart_data = []
    for year in range(start_year, current_year + 1):
        chart_data.append({
            "year": year,
            "articles": article_counts.get(year, 0),
            "researches": research_counts.get(year, 0),
        })

    return StandardResponse(
        success=True,
        message="Statistics fetched successfully",
        data={
            "range": year_range,
            "year_start": start_year,
            "year_end": current_year,
            "chart_data": chart_data
        }
    )
