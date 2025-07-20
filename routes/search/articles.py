from fastapi import APIRouter, Depends, HTTPException, Query, Path
from schemas import  ArticleResponse, ArticleAuthorResponse, ArticleResponseNoAbstract, ArticleAuthorNoAvatarResponse, StandardResponse
from typing import Optional
from models import User, Article
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func, case
from fastapi import Query
from services.article_services import get_all_articles_service, search_articles_by_authors_service, search_articles_by_title_service, get_article_detail_service


router = APIRouter(
    tags=['Articles Search']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()


@router.get("/articles", response_model=StandardResponse)
def get_all_articles_route(
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, SINTA"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    sort_by_citation: bool = Query(False, description="Sort by citation_count descending"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    result = get_all_articles_service(
        db=db,
        source=source,
        min_year=min_year,
        max_year=max_year,
        sort_by_citation=sort_by_citation,
        page=page,
        limit=limit
    )

    return StandardResponse(
        success=True,
        message="Articles fetched successfully",
        data=result
    )


@router.get("/search/articles/authors", response_model=StandardResponse)
def search_articles_by_authors(
    name: str = Query(..., description="Author name to search"),
    source: str = Query(None, description="Filter by source: SCOPUS, SINTA"),
    min_year: int = Query(None),
    max_year: int = Query(None),
    sort_by_citation: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    data = search_articles_by_authors_service(
        name=name,
        source=source,
        min_year=min_year,
        max_year=max_year,
        sort_by_citation=sort_by_citation,
        page=page,
        limit=limit,
        db=db
    )
    return StandardResponse(
        success=True, 
        message=f"Articles for '{name}' fetched successfully", 
        data=data
    )


@router.get("/search/articles/title", response_model=StandardResponse)
def search_articles_by_title(
    title: str = Query(..., description="Judul artikel yang ingin dicari"),
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, SINTA"),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    sort_by_citation: Optional[bool] = Query(False, description="Urutkan berdasarkan jumlah sitasi"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    total, articles = search_articles_by_title_service(
        title, source, min_year, max_year, sort_by_citation, page, limit, db
    )

    return StandardResponse(
        success=True,
        message=f"Articles with title containing '{title}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": articles
        }
    )


@router.get("/articles/{article_id}", response_model=StandardResponse)
def get_article_detail(
    article_id: int = Path(..., description="ID artikel publikasi"),
    db: Session = Depends(get_db)
):
    response_data = get_article_detail_service(article_id, db)
    return StandardResponse(
        success=True,
        message="Detail artikel berhasil diambil.",
        data=response_data
    )
