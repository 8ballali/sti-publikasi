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
    year_range: int = Query(0, ge=0, le=10, description="0=all years, 1=last year, 3=last 3 years, 6=last 6 years"),
    db: Session = Depends(get_db)
):
    current_year = datetime.now().year
    sources = ["SCOPUS", "GARUDA"]
    result = {}

    for source in sources:
        query = db.query(func.count(Article.id)).filter(Article.source.ilike(f"%{source}%"))

        if year_range > 0:
            min_year = current_year - year_range + 1
            query = query.filter(Article.year >= min_year)
            range_desc = f"sejak tahun {min_year}"
        elif year_range == 0:
            range_desc = "seluruh tahun"

        count = query.scalar() or 0

        # Ganti label "GARUDA" jadi "SINTA" untuk frontend
        label = "SINTA" if source == "GARUDA" else source
        result[label] = count

    return StandardResponse(
        success=True,
        message=f"Statistik jumlah artikel berdasarkan sumber {range_desc} berhasil diambil.",
        data=result
    )


