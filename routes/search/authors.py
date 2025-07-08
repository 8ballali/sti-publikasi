from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import AuthorDetailResponse, ArticleResponse, ResearchResponse, ArticleAuthorResponse
from repository.author_crawl import get_top_authors
from typing import Optional
from models import Author, User, PublicationAuthor, Article, Research, ResearcherAuthor
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func
from schemas import StandardResponse
from fastapi import Query


router = APIRouter()

router = APIRouter(
    tags=['Ladderboard & Author Detail']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()

@router.get("/stats/top-authors/articles")
def get_top_authors_articles(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Author.id.label("author_id"),
            User.name.label("name"),
            User.npp.label("npp"),
            func.count(PublicationAuthor.article_id).label("article_count")
        )
        .join(User, Author.user_id == User.id)
        .join(PublicationAuthor, PublicationAuthor.author_id == Author.id)
        .group_by(Author.id, User.name, User.npp)
        .order_by(func.count(PublicationAuthor.article_id).desc())
        .limit(limit)
        .all()
    )

    data = []
    for idx, r in enumerate(results, start=1):
        avatar_url = f"https://simpeg.dinus.ac.id/updir/small_med_{r.npp}.jpg" if r.npp else None
        data.append({
            "rank": idx,
            "author_id": r.author_id,
            "name": r.name or "-",
            "article_count": r.article_count,
            "avatar": avatar_url
        })

    return {
        "success": True,
        "message": "Top authors by articles fetched successfully",
        "data": data
    }

@router.get("/stats/top-authors/researches")
def get_top_authors_researches(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Author.id.label("author_id"),
            User.name.label("name"),
            User.npp.label("npp"),
            func.count(ResearcherAuthor.researcher_id).label("research_count")
        )
        .join(User, Author.user_id == User.id)
        .join(ResearcherAuthor, ResearcherAuthor.author_id == Author.id)
        .group_by(Author.id, User.name, User.npp)
        .order_by(func.count(ResearcherAuthor.researcher_id).desc())
        .limit(limit)
        .all()
    )

    data = []
    for idx, r in enumerate(results, start=1):
        avatar_url = f"https://simpeg.dinus.ac.id/updir/small_med_{r.npp}.jpg" if r.npp else None
        data.append({
            "rank": idx,
            "author_id": r.author_id,
            "name": r.name or "-",
            "research_count": r.research_count,
            "avatar": avatar_url
        })

    return {
        "success": True,
        "message": "Top authors by researches fetched successfully",
        "data": data
    }



@router.get("/authors/{author_id}", response_model=StandardResponse)
def get_author_detail(
    author_id: int,
    db: Session = Depends(get_db),
    article_page: int = Query(1, ge=1),
    article_limit: int = Query(10, ge=1, le=100),
    research_page: int = Query(1, ge=1),
    research_limit: int = Query(10, ge=1, le=100)
):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        return StandardResponse(success=False, message="Author not found", data=None)

    user = author.user
    subjects = [us.subject.name for us in author.subjects if us.subject]

    # ==== ARTICLES with pagination ====
    sorted_publications = sorted(
        author.publications,
        key=lambda x: (x.author_order if x.author_order is not None else 9999)
    )
    article_start = (article_page - 1) * article_limit
    article_end = article_start + article_limit
    paginated_articles = sorted_publications[article_start:article_end]

    articles = []
    for pa in paginated_articles:
        a = pa.article
        if a:
            # Ambil semua authors untuk artikel ini
            author_list = sorted([
                ArticleAuthorResponse(
                    author_id=apa.author.id,
                    author_name=apa.author.user.name,
                    author_order=apa.author_order
                )
                for apa in a.authors
                if apa.author and apa.author.user
            ], key=lambda x: x.author_order or 9999)

            articles.append(ArticleResponse(
                id=a.id,
                title=a.title,
                accred=a.accred,
                abstract=a.abstract,
                year=a.year,
                article_url=a.article_url,
                journal=a.journal,
                doi=a.doi,
                citation_count=a.citation_count,
                source=a.source,
                authors=author_list
            ))

    # ==== RESEARCHES with pagination ====
    all_researches = author.research
    research_start = (research_page - 1) * research_limit
    research_end = research_start + research_limit
    paginated_researches = all_researches[research_start:research_end]

    researches = []
    for ra in paginated_researches:
        r = ra.research
        if not r:
            continue

        personils_list = [
            x.author.user.name for x in r.authors
            if x.author and x.author.user and x.author.id != author.id
        ]
        personils = "; ".join(personils_list) if personils_list else None

        researches.append(ResearchResponse(
            title=r.title,
            leader_name=r.leader_name or "Unknown",
            jenis_penelitian=r.fund_type,
            personils=personils,
            year=r.year,
            dana_penelitian=r.fund,
            status_penelitian=r.fund_status,
            sumber_pendanaan=r.fund_source,
            author_id=author.id,
            author_name=user.name
        ))

    # ==== Bikin URL avatar dari NPP ====
    npp = user.npp
    avatar_url = f"https://simpeg.dinus.ac.id/updir/small_med_{npp}.jpg" if npp else None

    # ==== FINAL RESPONSE ====
    author_detail = AuthorDetailResponse(
        id=author.id,
        name=user.name,
        avatar=avatar_url,
        sinta_profile_url=author.sinta_profile_url,
        sinta_score_3yr=author.sinta_score_3yr,
        sinta_score_total=author.sinta_score_total,
        affil_score_3yr=author.affil_score_3yr,
        affil_score_total=author.affil_score_total,
        subjects=subjects,
        articles=articles,
        researches=researches,
        
    )

    return StandardResponse(
        success=True,
        message="Authors fetched successfully",
        data=author_detail
    )

