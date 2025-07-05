from fastapi import APIRouter, Depends, HTTPException, Query, Path
from schemas import  ArticleResponse, ArticleAuthorResponse
from repository.author_crawl import get_top_authors
from typing import Optional
from models import Author,User, PublicationAuthor, Article
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func, case
from schemas import StandardResponse
from fastapi import Query


router = APIRouter(
    tags=['Articles Search']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()


@router.get("/articles", response_model=StandardResponse)
def get_all_articles(
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, SINTA"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    sort_by_citation: bool = Query(False, description="Sort by citation_count descending"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Article)

    if source:
        query = query.filter(Article.source.ilike(f"%{source.upper()}%"))

    if min_year is not None:
        query = query.filter(Article.year >= min_year)
    if max_year is not None:
        query = query.filter(Article.year <= max_year)

    if sort_by_citation:
        query = query.order_by(
            case((Article.citation_count == None, 1), else_=0),
            Article.citation_count.desc()
        )
    else:
        query = query.order_by(Article.year.desc())

    total = query.count()

    paginated = query.offset((page - 1) * limit).limit(limit).all()

    articles_data = []
    for article in paginated:
        author_list = []
        for pa in article.authors:
            if pa.author and pa.author.user:
                author_list.append(ArticleAuthorResponse(
                    author_id=pa.author.id,
                    author_name=pa.author.user.name,
                    author_order=pa.author_order
                ))

        articles_data.append(ArticleResponse(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            accred=article.accred,
            abstract=article.abstract,
            citation_count=article.citation_count,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            authors=author_list
        ))

    return StandardResponse(
        success=True,
        message="Articles fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": articles_data
        }
    )

@router.get("/search/articles/authors", response_model=StandardResponse)
def search_articles_by_authors(
    name: str = Query(..., description="Author name to search"),
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, SINTA"),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    sort_by_citation: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Temukan user berdasarkan nama
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    matched_author_ids = [user.author.id for user in users if user.author]
    if not matched_author_ids:
        raise HTTPException(status_code=404, detail="Authors found but no associated author records")

    # Temukan semua artikel yang memiliki author tersebut
    article_set = set()
    for author_id in matched_author_ids:
        pa_records = db.query(Article).join(Article.authors).filter_by(author_id=author_id).all()
        article_set.update(pa_records)

    # Filter
    filtered_articles = []
    for article in article_set:
        if source and (not article.source or source.upper() not in article.source.upper()):
            continue
        if min_year and article.year and article.year < min_year:
            continue
        if max_year and article.year and article.year > max_year:
            continue
        filtered_articles.append(article)

    # Sort
    if sort_by_citation:
        filtered_articles.sort(
            key=lambda x: (x.citation_count is None, -(x.citation_count or 0))
        )
    else:
        filtered_articles.sort(
            key=lambda x: x.year if x.year else 0, reverse=True
        )

    # Pagination
    total = len(filtered_articles)
    start = (page - 1) * limit
    end = start + limit
    paginated = filtered_articles[start:end]

    # Response dengan list penulis lengkap
    articles_response = []
    for article in paginated:
        author_list = []
        for pa in article.authors:
            if pa.author and pa.author.user:
                author_list.append(ArticleAuthorResponse(
                    author_id=pa.author.id,
                    author_name=pa.author.user.name,
                    author_order=pa.author_order
                ))
        articles_response.append(ArticleResponse(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            accred=article.accred,
            abstract=article.abstract,
            citation_count=article.citation_count,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            authors=author_list
        ))

    return StandardResponse(
        success=True,
        message=f"Articles for '{name}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": articles_response
        }
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
    # Query dasar: cari berdasarkan judul
    query = db.query(Article).filter(
        func.lower(Article.title).like(f"%{title.lower()}%")
    )

    # Filter source
    if source:
        query = query.filter(Article.source.ilike(f"%{source.upper()}%"))

    # Filter tahun
    if min_year:
        query = query.filter(Article.year >= min_year)
    if max_year:
        query = query.filter(Article.year <= max_year)

    # Sorting
    if sort_by_citation:
        query = query.order_by(
            case((Article.citation_count == None, 1), else_=0),
            Article.citation_count.desc()
        )
    else:
        query = query.order_by(Article.year.desc())

    total = query.count()
    articles = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for article in articles:
        author_list = []
        for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
            if pa.author and pa.author.user:
                author_list.append(ArticleAuthorResponse(
                    author_id=pa.author.id,
                    author_name=pa.author.user.name,
                    author_order=pa.author_order
                ))

        result.append(ArticleResponse(
            id=article.id,
            title=article.title,
            accred=article.accred,
            year=article.year,
            doi=article.doi,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            abstract=article.abstract,
            citation_count=article.citation_count,
            authors=author_list
        ))

    return StandardResponse(
        success=True,
        message=f"Articles with title containing '{title}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": result
        }
    )





@router.get("/articles/{article_id}", response_model=StandardResponse)
def get_article_detail(
    article_id: int = Path(..., description="ID artikel publikasi"),
    db: Session = Depends(get_db)
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Ambil semua authors
    author_list = []
    for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
        if pa.author and pa.author.user:
            author_list.append(ArticleAuthorResponse(
                author_id=pa.author.id,
                author_name=pa.author.user.name,
                author_order=pa.author_order
            ))

    response_data = ArticleResponse(
        id=article.id,
        title=article.title,
        accred=article.accred,
        abstract=article.abstract,
        year=article.year,
        article_url=article.article_url,
        journal=article.journal,
        doi=article.doi,
        citation_count=article.citation_count,
        source=article.source,
        authors=author_list
    )

    return StandardResponse(
        success=True,
        message="Detail artikel berhasil diambil.",
        data=response_data
    )

