from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import ResearchResponse
from typing import Optional, Literal
from models import User,Research
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func, case
from schemas import StandardResponse
from fastapi import Query
from services.research_services import get_all_researches_service, search_researches_by_authors_service, search_researches_by_title_service


router = APIRouter(
    tags=['Researches Search']
)


@router.get("/researches", response_model=StandardResponse)
def get_all_researches(
    min_year: Optional[int] = Query(None, description="Tahun minimal"),
    max_year: Optional[int] = Query(None, description="Tahun maksimal"),
    termahal: bool = Query(False, description="Urutkan berdasarkan dana terbanyak"),
    fund_source: Optional[
        Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]
    ] = Query(None, description="Sumber dana penelitian"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    data = get_all_researches_service(
        db=db,
        min_year=min_year,
        max_year=max_year,
        termahal=termahal,
        fund_source=fund_source,
        page=page,
        limit=limit
    )

    return StandardResponse(
        success=True,
        message="Daftar penelitian berhasil diambil.",
        data=data
    )


@router.get("/search/researches/authors", response_model=StandardResponse)
def search_researches_by_authors(
    name: str = Query(..., description="Author name to search"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    fund_source: Optional[
        Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]
    ] = Query(None, description="Filter by fund source"),
    termahal: bool = Query(False, description="Sort by highest fund"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return search_researches_by_authors_service(
        db=db,
        name=name,
        min_year=min_year,
        max_year=max_year,
        fund_source=fund_source,
        termahal=termahal,
        page=page,
        limit=limit
    )


@router.get("/search/researches/title", response_model=StandardResponse)
def search_researches_by_title(
    title: str = Query(..., description="Judul penelitian yang ingin dicari"),
    min_year: Optional[int] = Query(None, description="Tahun minimal"),
    max_year: Optional[int] = Query(None, description="Tahun maksimal"),
    fund_source: Optional[
        Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]
    ] = Query(None, description="Filter berdasarkan sumber pendanaan"),
    termahal: bool = Query(False, description="Urutkan berdasarkan dana terbanyak"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return search_researches_by_title_service(
        db=db,
        title=title,
        min_year=min_year,
        max_year=max_year,
        fund_source=fund_source,
        termahal=termahal,
        page=page,
        limit=limit
    )
