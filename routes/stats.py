from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models import Author, Article, Research
from database import get_db
from schemas import StandardResponse  # pastikan diimport
from sqlalchemy import func
from datetime import datetime

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


@router.get("/stats/chart", response_model=StandardResponse)
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

        count = query.scalar() or 0

        # Ganti label "GARUDA" jadi "SINTA" untuk frontend
        label = "SINTA" if source == "GARUDA" else source
        result[label] = count

    return StandardResponse(
        success=True,
        message="Statistik jumlah artikel berdasarkan sumber berhasil diambil.",
        data=result
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

    count = query.scalar() or 0

    return StandardResponse(
        success=True,
        message=f"Statistik jumlah penelitian {f'{year_range} tahun terakhir' if year_range > 0 else '(semua tahun)'} berhasil diambil.",
        data={"total_researches": count}
    )