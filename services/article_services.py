from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Tuple, Optional
from sqlalchemy import case
from models import Article
from schemas import ArticleResponseNoAbstract, ArticleAuthorNoAvatarResponse, ArticleResponse, ArticleAuthorResponse
from sqlalchemy import func
from fastapi import HTTPException
from models import User, Article

def get_all_articles_service(
    db: Session,
    source: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    sort_by_citation: bool = False,
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:

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
        for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
            if pa.author and pa.author.user:
                user = pa.author.user
                author_list.append(ArticleAuthorNoAvatarResponse(
                    author_id=pa.author.id,
                    author_name=user.name,
                    author_order=pa.author_order
                ))

        articles_data.append(ArticleResponseNoAbstract(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            accred=article.accred,
            citation_count=article.citation_count,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            authors=author_list
        ))

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "articles": articles_data
    }


def search_articles_by_authors_service(
    name: str,
    source: str,
    min_year: int,
    max_year: int,
    sort_by_citation: bool,
    page: int,
    limit: int,
    db: Session
):
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    matched_author_ids = [user.author.id for user in users if user.author]
    if not matched_author_ids:
        raise HTTPException(status_code=404, detail="Authors found but no associated author records")

    article_set = set()
    for author_id in matched_author_ids:
        pa_records = db.query(Article).join(Article.authors).filter_by(author_id=author_id).all()
        article_set.update(pa_records)

    filtered_articles = []
    for article in article_set:
        if source and (not article.source or source.upper() not in article.source.upper()):
            continue
        if min_year and article.year and article.year < min_year:
            continue
        if max_year and article.year and article.year > max_year:
            continue
        filtered_articles.append(article)

    if sort_by_citation:
        filtered_articles.sort(key=lambda x: (x.citation_count is None, -(x.citation_count or 0)))
    else:
        filtered_articles.sort(key=lambda x: x.year if x.year else 0, reverse=True)

    total = len(filtered_articles)
    start = (page - 1) * limit
    end = start + limit
    paginated = filtered_articles[start:end]

    articles_response = []
    for article in paginated:
        author_list = []
        for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
            if pa.author and pa.author.user:
                user = pa.author.user
                author_list.append(ArticleAuthorNoAvatarResponse(
                    author_id=pa.author.id,
                    author_name=user.name,
                    author_order=pa.author_order
                ))

        articles_response.append(ArticleResponseNoAbstract(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            accred=article.accred,
            citation_count=article.citation_count,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            authors=author_list
        ))

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "articles": articles_response
    }

def search_articles_by_title_service(
    title: str,
    source: Optional[str],
    min_year: Optional[int],
    max_year: Optional[int],
    sort_by_citation: Optional[bool],
    page: int,
    limit: int,
    db: Session
) -> Tuple[int, List[ArticleResponseNoAbstract]]:

    query = db.query(Article).filter(
        func.lower(Article.title).like(f"%{title.lower()}%")
    )

    if source:
        query = query.filter(Article.source.ilike(f"%{source.upper()}%"))

    if min_year:
        query = query.filter(Article.year >= min_year)
    if max_year:
        query = query.filter(Article.year <= max_year)

    if sort_by_citation:
        query = query.order_by(
            case((Article.citation_count == None, 1), else_=0),
            Article.citation_count.desc()
        )
    else:
        query = query.order_by(Article.year.desc())

    total = query.count()
    articles = query.offset((page - 1) * limit).limit(limit).all()

    results = []
    for article in articles:
        author_list = []
        for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
            if pa.author and pa.author.user:
                user = pa.author.user
                author_list.append(ArticleAuthorNoAvatarResponse(
                    author_id=pa.author.id,
                    author_name=user.name,
                    author_order=pa.author_order
                ))

        results.append(ArticleResponseNoAbstract(
            id=article.id,
            title=article.title,
            accred=article.accred,
            year=article.year,
            doi=article.doi,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            citation_count=article.citation_count,
            authors=author_list
        ))

    return total, results


def get_article_detail_service(article_id: int, db: Session) -> ArticleResponse:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    author_list = []
    for pa in sorted(article.authors, key=lambda x: x.author_order or 9999):
        if pa.author and pa.author.user:
            user = pa.author.user
            npp = user.npp
            avatar_url = f"https://simpeg.dinus.ac.id/updir/small_med_{npp}.jpg" if npp else None

            author_list.append(ArticleAuthorResponse(
                author_id=pa.author.id,
                author_name=user.name,
                author_order=pa.author_order,
                avatar=avatar_url
            ))

    return ArticleResponse(
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