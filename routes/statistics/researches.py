from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import Author, Article, Research
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime

router = APIRouter(
    tags=['Statistics Researches']
)



@router.get("/stats/research/fund", response_model=StandardResponse)
def get_fund_statistics(
    year_range: int = Query(0, ge=0, le=10, description="Filter jumlah tahun terakhir (0 = semua tahun)"),
    db: Session = Depends(get_db)
):
    sources = ["INTERNAL SOURCE", "BIMA SOURCE", "SIMLITABMAS SOURCE"]
    current_year = datetime.now().year

    stats = {}
    for source in sources:
        query = db.query(
            func.sum(Research.fund).label("total_fund"),
            func.count(Research.id).label("total_count")
        ).filter(func.upper(Research.fund_source) == source)

        # Jika filter tahun diaktifkan
        if year_range > 0:
            min_year = current_year - year_range + 1
            query = query.filter(Research.year >= min_year)

        result = query.one()
        stats[source] = {
            "total_fund": result.total_fund or 0,
            "total_research": result.total_count or 0
        }

    return StandardResponse(
        success=True,
        message="Statistik dana riset berdasarkan sumber berhasil diambil.",
        data=stats
    )

@router.get("/stats/research/count", response_model=StandardResponse)
def get_research_stats(
    year_range: int = Query(0, ge=0, le=10, description="0=all years, 1=last year, 3=last 3 years, 6=last 6 years"),
    db: Session = Depends(get_db)
):
    current_year = datetime.now().year
    query = db.query(func.count(Research.id))

    if year_range > 0:
        min_year = current_year - year_range + 1
        query = query.filter(Research.year >= min_year)
        range_desc = f"sejak tahun {min_year}"
    else:
        range_desc = "untuk semua tahun"

    count = query.scalar() or 0

    return StandardResponse(
        success=True,
        message=f"Statistik jumlah penelitian {range_desc} berhasil diambil.",
        data={"total_researches": count}
    )
