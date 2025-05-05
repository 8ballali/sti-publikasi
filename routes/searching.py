from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from schemas import  ArticleAuthorItem, ArticleWithAuthorsResponse, AuthorDetailResponse, SubjectItem
from typing import List
from models import PublicationAuthor, Article, User
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func


router = APIRouter()

router = APIRouter(
    tags=['Searching General']
)

@router.get("/authors/search", response_model=List[AuthorDetailResponse])
def search_authors_by_name(name: str, db: Session = Depends(get_db)):
    # Case-insensitive search
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()

    if not users:
        raise HTTPException(status_code=404, detail="Author not found")

    results = []
    for user in users:
        author = user.author
        if not author:
            continue

        # Ambil semua subject yang terkait
        subject_items = [
            SubjectItem(id=us.subject.id, name=us.subject.name)
            for us in author.subjects if us.subject
        ]

        results.append(AuthorDetailResponse(
            id=author.id,
            name=user.name,
            sinta_profile_url=author.sinta_profile_url,
            sinta_score_3yr=author.sinta_score_3yr,
            sinta_score_total=author.sinta_score_total,
            affil_score_3yr=author.affil_score_3yr,
            affil_score_total=author.affil_score_total,
            subjects=subject_items
        ))

    return results


@router.get("/articles/search", response_model=List[ArticleWithAuthorsResponse])
def search_articles_by_title(title: str, db: Session = Depends(get_db)):
    articles = db.query(Article).filter(Article.title.ilike(f"%{title}%")).all()

    results = []
    for article in articles:
        authors = []

        for pa in article.authors:
            author_user = pa.author.user
            if author_user:
                authors.append(ArticleAuthorItem(
                    name=author_user.name,
                    author_order=pa.author_order
                ))

        results.append(ArticleWithAuthorsResponse(
            id=article.id,
            title=article.title,
            year=article.year,
            doi=article.doi,
            accred=article.accred,
            citation_count=article.citation_count,
            article_url=article.article_url,
            journal=article.journal,
            source=article.source,
            authors=authors
        ))

    return results

