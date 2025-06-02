from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from schemas import  ArticleAuthorItem, ArticleWithAuthorsResponse, AuthorDetailResponse, AuthorSearchResponse, ArticleResponse, ResearchResponse
from typing import List
from models import Author,Article,User
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func
from schemas import StandardResponse


router = APIRouter()

router = APIRouter(
    tags=['Searching General']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()

@router.get("/search/articles", response_model=StandardResponse)
def search_articles(
    name: str = Query(..., description="Author name to search"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    # Cari user berdasar nama (case insensitive)
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    # Kumpulkan semua articles dari semua authors yang ditemukan
    articles_query = []
    for user in users:
        author = user.author
        if not author:
            continue
        for pa in author.publications:
            if pa.article:
                articles_query.append(pa)

    total = len(articles_query)
    # pagination manual karena ini list, bisa ganti ke query db kalau struktur db memungkinkan join lebih kompleks
    start = (page - 1) * limit
    end = start + limit
    articles_page = articles_query[start:end]

    articles = [
        ArticleResponse(
            id=pa.article.id,
            title=pa.article.title,
            year=pa.article.year,
            article_url=pa.article.article_url,
            journal=pa.article.journal,
            source=pa.article.source,
            author_order=pa.author_order
        )
        for pa in articles_page
    ]

    return StandardResponse(
        success=True,
        message=f"Articles for '{name}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "articles": articles,
        }
    )


@router.get("/search/researches", response_model=StandardResponse)
def search_researches(
    name: str = Query(..., description="Author name to search"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    researches_query = []
    for user in users:
        author = user.author
        if not author:
            continue
        for ra in author.research:
            research = ra.research
            if not research:
                continue
            # Leader
            leader = next(
                (r.author.user.name for r in research.authors if r.is_leader and r.author and r.author.user),
                "Unknown"
            )
            # Personils
            personils = "; ".join([
                r.author.user.name for r in research.authors if r.author and r.author.user and not r.is_leader
            ])

            researches_query.append(
                ResearchResponse(
                    title=research.title,
                    leader=leader,
                    jenis_penelitian=research.fund_type,
                    personils=personils,
                    year=research.year,
                    dana_penelitian=research.fund,
                    status_penelitian=research.fund_status,
                    sumber_pendanaan=research.fund_source
                )
            )

    total = len(researches_query)
    start = (page - 1) * limit
    end = start + limit
    researches_page = researches_query[start:end]

    return StandardResponse(
        success=True,
        message=f"Researches for '{name}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "researches": researches_page,
        }
    )


@router.get("/authors/{author_id}", response_model=StandardResponse)
def get_author_detail(author_id: int, db: Session = Depends(get_db)):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        return StandardResponse(success=False, message="Author not found", data=None)

    user = author.user

    subjects = [us.subject.name for us in author.subjects if us.subject]

    articles = []
    for pa in sorted(author.publications, key=lambda x: (x.author_order if x.author_order is not None else 9999)):
        a = pa.article
        if a:
            articles.append(ArticleResponse(
                id=a.id,
                title=a.title,
                year=a.year,
                article_url=a.article_url,
                journal=a.journal,
                source=a.source,
                author_order=pa.author_order
            ))

    researches = []
    for ra in author.research:
        r = ra.research
        if not r:
            continue

        leader_ra = next((x for x in r.authors if x.is_leader), None)
        leader_name = leader_ra.author.user.name if leader_ra and leader_ra.author and leader_ra.author.user else "Unknown"

        personils_list = [
            x.author.user.name for x in r.authors
            if x.author and x.author.user and not x.is_leader
        ]
        personils = ", ".join(personils_list) if personils_list else None

        researches.append(ResearchResponse(
            title=r.title,
            leader=leader_name,
            jenis_penelitian=r.fund_type,
            personils=personils,
            year=r.year,
            dana_penelitian=r.fund,
            status_penelitian=r.fund_status,
            sumber_pendanaan=r.fund_source
        ))

    author_detail = AuthorDetailResponse(
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
    )

    return StandardResponse(
        success=True,
        message="Authors fetched successfully",
        data=author_detail
    )


