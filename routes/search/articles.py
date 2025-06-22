from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import  ArticleResponse
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
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, GARUDA"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    sort_by_citation: bool = Query(False, description="Sort by citation_count descending"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(PublicationAuthor).join(Article).join(Author).join(User)

    if source:
        query = query.filter(Article.source.ilike(f"%{source.upper()}%"))

    if min_year is not None:
        query = query.filter(Article.year >= min_year)
    if max_year is not None:
        query = query.filter(Article.year <= max_year)

    if sort_by_citation:
        # MariaDB-compatible: sort NULLs last
        query = query.order_by(
            case((Article.citation_count == None, 1), else_=0),
            Article.citation_count.desc()
        )
    else:
        query = query.order_by(Article.year.desc())

    total = query.count()

    paginated = query.offset((page - 1) * limit).limit(limit).all()

    articles_data = [
        ArticleResponse(
            id=pa.article.id,
            title=pa.article.title,
            abstract=pa.article.abstract,
            year=pa.article.year,
            article_url=pa.article.article_url,
            journal=pa.article.journal,
            doi=pa.article.doi,
            citation_count=pa.article.citation_count,
            source=pa.article.source,
            author_order=pa.author_order,
            author_id=pa.author.id if pa.author else 0,
            author_name=pa.author.user.name if pa.author and pa.author.user else "Unknown"
        )
        for pa in paginated
    ]

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
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, GARUDA"),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    sort_by_citation: Optional[bool] = Query(False, description="Sort by citation count"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    articles_query = []
    for user in users:
        author = user.author
        if not author:
            continue
        for pa in author.publications:
            if not pa.article:
                continue
            article = pa.article

            # Filter berdasarkan source
            if source and article.source != source.upper():
                continue

            # Filter tahun
            if min_year and article.year and article.year < min_year:
                continue
            if max_year and article.year and article.year > max_year:
                continue

            articles_query.append({
                "article": article,
                "author_name": user.name,
                "author_id": author.id,
                "author_order": pa.author_order
            })

    # Sorting
    if sort_by_citation:
        articles_query.sort(
            key=lambda x: (x["article"].citation_count is None, -(x["article"].citation_count or 0))
        )
    else:
        articles_query.sort(
            key=lambda x: x["article"].year if x["article"].year else 0, reverse=True
        )

    # Pagination
    total = len(articles_query)
    start = (page - 1) * limit
    end = start + limit
    paginated = articles_query[start:end]

    articles = [
        ArticleResponse(
            id=item["article"].id,
            title=item["article"].title,
            year=item["article"].year,
            doi=item["article"].doi,
            article_url=item["article"].article_url,
            journal=item["article"].journal,
            source=item["article"].source,
            author_order=item["author_order"],
            author_name=item["author_name"],
            author_id=item["author_id"]
        )
        for item in paginated
    ]

    return StandardResponse(
        success=True,
        message=f"Articles for '{name}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": articles
        }
    )



@router.get("/search/articles/title", response_model=StandardResponse)
def search_articles_by_title(
    title: str = Query(..., description="Judul artikel yang ingin dicari"),
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, GARUDA"),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    sort_by_citation: Optional[bool] = Query(False, description="Urutkan berdasarkan jumlah sitasi"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Query artikel yang judulnya mirip
    articles_query = db.query(Article).filter(
        func.lower(Article.title).like(f"%{title.lower()}%")
    )

    # Filter source
    if source:
        articles_query = articles_query.filter(Article.source == source.upper())

    # Filter tahun
    if min_year:
        articles_query = articles_query.filter(Article.year >= min_year)
    if max_year:
        articles_query = articles_query.filter(Article.year <= max_year)

    articles_list = articles_query.all()

    # Sorting
    if sort_by_citation:
        articles_list.sort(key=lambda x: (x.citation_count is None, -(x.citation_count or 0)))
    else:
        articles_list.sort(key=lambda x: x.year if x.year else 0, reverse=True)

    # Pagination
    total = len(articles_list)
    start = (page - 1) * limit
    end = start + limit
    paginated = articles_list[start:end]

    articles = []
    for article in paginated:
        authorships = article.authors  # relasi PublicationAuthor
        sorted_authors = sorted(authorships, key=lambda x: x.author_order or 9999)

        author_order = None
        author_name = None
        author_id = None
        if sorted_authors:
            first_author = sorted_authors[0]
            if first_author.author and first_author.author.user:
                author_order = first_author.author_order
                author_name = first_author.author.user.name
                author_id = first_author.author.id

        articles.append(ArticleResponse(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            author_order=author_order,
            author_name=author_name,
            author_id=author_id
        ))

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
