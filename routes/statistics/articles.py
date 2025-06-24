from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import  Article
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime

router = APIRouter()
router = APIRouter(
    tags=['Statistics Articles']
)

@router.get("/stats/articles/source", response_model=StandardResponse)
def get_article_stats_by_source(
    year_range: int = Query(6, ge=1, le=10, description="Rentang tahun ke belakang (default: 6 tahun)"),
    db: Session = Depends(get_db)
):
    current_year = datetime.now().year
    start_year = current_year - year_range + 1
    sources = ["SCOPUS", "GARUDA"]
    result = {}

    for source in sources:
        source_label = "SINTA" if source == "GARUDA" else source
        yearly_data = {}

        for year in range(current_year, start_year - 1, -1):  # dari tahun sekarang mundur
            count = (
                db.query(func.count(Article.id))
                .filter(Article.source.ilike(f"%{source}%"), Article.year == year)
                .scalar()
            )
            yearly_data[str(year)] = count or 0

        result[source_label] = yearly_data

    return StandardResponse(
        success=True,
        message=f"Statistik jumlah artikel per tahun berdasarkan sumber sejak tahun {start_year} berhasil diambil.",
        data=result
    )

