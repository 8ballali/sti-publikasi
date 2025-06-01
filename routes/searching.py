from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from schemas import  ArticleAuthorItem, ArticleWithAuthorsResponse, AuthorDetailResponse, SubjectItem, ArticleResponse, ResearchResponse
from typing import List
from models import PublicationAuthor, Article, User
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func


router = APIRouter()

router = APIRouter(
    tags=['Searching General']
)

@router.get("/search/authors", response_model=List[AuthorDetailResponse])
def search_authors_by_name(name: str, db: Session = Depends(get_db)):
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()

    if not users:
        raise HTTPException(status_code=404, detail="Author not found")

    results = []
    for user in users:
        author = user.author
        if not author:
            continue

        # Subjects
        subjects = [
            us.subject.name
            for us in author.subjects
            if us.subject and us.subject.name
        ]

        # Articles
        articles = [
            ArticleResponse(
                id=pa.article.id,
                title=pa.article.title,
                year=pa.article.year,
                journal=pa.article.journal,
                source=pa.article.source,
                article_url=pa.article.article_url,
                author_order=pa.author_order
            )
            for pa in author.publications if pa.article
        ]

        # Researches
        researches = []
        for ra in author.research:
            research = ra.research
            if not research:
                continue

            # Get leader and personils
            leader_name = None
            personils = []

            for r_auth in research.authors:
                if r_auth.is_leader:
                    leader_name = r_auth.author.user.name if r_auth.author and r_auth.author.user else "Unknown"
                elif r_auth.author and r_auth.author.user:
                    personils.append(r_auth.author.user.name)

            researches.append(ResearchResponse(
                title=research.title,
                leader=leader_name or "Unknown",
                jenis_penelitian=research.fund_type or "-",
                personils=", ".join(personils) if personils else None,
                year=str(research.year) if research.year else None,
                dana_penelitian=f"Rp{int(research.fund):,}" if research.fund else "-",
                status_penelitian=research.fund_status or "-",
                sumber_pendanaan=research.fund_source or "-"
            ))

        results.append(AuthorDetailResponse(
            id=author.id,
            name=user.name,
            sinta_profile_url=author.sinta_profile_url,
            sinta_score_3yr=author.sinta_score_3yr,
            sinta_score_total=author.sinta_score_total,
            affil_score_3yr=author.affil_score_3yr,
            affil_score_total=author.affil_score_total,
            subjects=subjects,
            articles=articles,
            researches=researches
        ))

    return results



@router.get("/search/articles", response_model=List[ArticleWithAuthorsResponse])
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

