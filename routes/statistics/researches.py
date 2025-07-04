from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import Author, Article, Research
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict

router = APIRouter(
    tags=['Statistics Researches']
)



@router.get("/stats/research/fund", response_model=StandardResponse)
def get_fund_statistics(
    year_range: int = Query(6, ge=0, le=10, description="Filter jumlah tahun terakhir (0 = semua tahun)"),
    db: Session = Depends(get_db)
):
    sources = ["INTERNAL SOURCE", "BIMA SOURCE", "SIMLITABMAS SOURCE"]
    current_year = datetime.now().year

    min_year = current_year - year_range + 1 if year_range > 0 else None

    # Siapkan struktur hasil
    stats = {source: {} for source in sources}
    total_all_fund = 0

    # Ambil daftar tahun yang tersedia
    years = (
        list(range(min_year, current_year + 1))
        if min_year else
        db.query(Research.year).distinct().filter(Research.year.isnot(None)).order_by(Research.year).all()
    )

    # Pastikan years adalah list tahun integer
    if not isinstance(years[0], int):
        years = [y[0] for y in years]

    for year in years:
        for source in sources:
            query = db.query(
                func.sum(Research.fund).label("total_fund")
            ).filter(
                func.upper(Research.fund_source) == source,
                Research.year == year
            )

            result = query.one()
            fund = result.total_fund or 0
            stats[source][str(year)] = {
                "total_fund": fund
            }

            total_all_fund += fund

    return StandardResponse(
        success=True,
        message="Statistik dana riset berdasarkan sumber dan tahun berhasil diambil.",
        data={
            "per_source": stats,
            "total_all_fund": total_all_fund
        }
    )


@router.get("/stats/research/total", response_model=StandardResponse)
def get_research_total(
    year_range: int = Query(6, ge=0, le=10, description="0=all years, 1=last year, 3=last 3 years, 6=last 6 years"),
    db: Session = Depends(get_db)
):
    current_year = datetime.now().year

    if year_range > 0:
        min_year = current_year - year_range + 1
        years = list(range(min_year, current_year + 1))
        range_desc = f"sejak tahun {min_year}"
    else:
        year_tuples = db.query(Research.year).distinct().filter(Research.year.isnot(None)).order_by(Research.year).all()
        years = [y[0] for y in year_tuples]
        range_desc = "untuk semua tahun"

    # Query total count by fund_source and year
    query = (
        db.query(Research.fund_source, Research.year, func.count(Research.id))
        .filter(Research.year.in_(years))
        .group_by(Research.fund_source, Research.year)
        .all()
    )

    # Susun hasilnya ke dalam nested dict
    result = defaultdict(dict)
    for fund_source, year, count in query:
        result[fund_source][str(year)] = count

    return StandardResponse(
        success=True,
        message=f"Statistik jumlah penelitian per tahun berdasarkan sumber {range_desc} berhasil diambil.",
        data=result
    )