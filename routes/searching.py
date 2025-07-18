from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import AuthorDetailResponse, ArticleResponse, ResearchResponse
from repository.author_crawl import get_top_authors
from typing import Optional
from models import Author,User, PublicationAuthor, Article, Research
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func
from schemas import StandardResponse
from fastapi import Query


router = APIRouter()

router = APIRouter(
    tags=['Searching General']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()

@router.get("/authors/top")
def top_authors(limit: int = 10, db: Session = Depends(get_db)):
    return get_top_authors(db, limit)

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
            articles.append(ArticleResponse(
                id=a.id,
                title=a.title,
                year=a.year,
                article_url=a.article_url,
                journal=a.journal,
                source=a.source,
                author_order=pa.author_order,
                author_id=pa.author.id,
                author_name=pa.author.user.name if pa.author and pa.author.user else "Unknown"
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
            sumber_pendanaan=r.fund_source,
            author_id=author.id,
            author_name=user.name
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


@router.get("/articles", response_model=StandardResponse)
def get_all_articles(
    source: Optional[str] = Query(None, description="Filter by source: SCOPUS, GARUDA, GOOGLE_SCHOLAR"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(PublicationAuthor).join(Article).join(Author).join(User)

    if source:
        query = query.filter(Article.source == source.upper())

    if min_year is not None:
        query = query.filter(Article.year >= min_year)
    if max_year is not None:
        query = query.filter(Article.year <= max_year)

    all_articles = query.all()

    # Sort by year descending (latest first)
    all_articles.sort(key=lambda x: x.article.year if x.article.year else 0, reverse=True)

    # Pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_articles = all_articles[start:end]

    articles_data = [
        ArticleResponse(
            id=pa.article.id,
            title=pa.article.title,
            abstract=pa.article.abstract,
            year=pa.article.year,
            article_url=pa.article.article_url,
            journal=pa.article.journal,
            doi=pa.article.doi,
            source=pa.article.source,
            author_order=pa.author_order,
            author_id=pa.author.id if pa.author else 0,
            author_name=pa.author.user.name if pa.author and pa.author.user else "Unknown"
        )
        for pa in paginated_articles
    ]

    return StandardResponse(
        success=True,
        message=f"Articles{' from ' + source if source else ''} fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": len(all_articles),
            "articles": articles_data
        }
    )

@router.get("/researches", response_model=StandardResponse)
def get_all_researches(
    min_fund: Optional[int] = Query(None, description="Minimum fund amount"),
    max_fund: Optional[int] = Query(None, description="Maximum fund amount"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    base_query = db.query(Research)

    # Filter fund
    if min_fund is not None:
        base_query = base_query.filter(Research.fund >= min_fund)
    if max_fund is not None:
        base_query = base_query.filter(Research.fund <= max_fund)

    # Filter year
    if min_year is not None:
        base_query = base_query.filter(Research.year >= min_year)
    if max_year is not None:
        base_query = base_query.filter(Research.year <= max_year)

    total = base_query.count()

    researches_raw = (
        base_query
        .order_by(func.isnull(Research.year), Research.year.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = []
    for research in researches_raw:
        leader = next(
            (
                r.author.user.name
                for r in research.authors
                if r.is_leader and r.author and r.author.user
            ),
            "Unknown"
        )

        personils = "; ".join([
            r.author.user.name
            for r in research.authors
            if r.author and r.author.user and not r.is_leader
        ])

        any_author = next(
            (r.author for r in research.authors if r.author and r.author.user),
            None
        )

        author_name = any_author.user.name if any_author else "Unknown"
        author_id = any_author.id if any_author else None

        results.append(ResearchResponse(
            title=research.title,
            leader=leader,
            jenis_penelitian=research.fund_type,
            personils=personils,
            year=research.year,
            dana_penelitian=research.fund,
            status_penelitian=research.fund_status,
            sumber_pendanaan=research.fund_source,
            author_name=author_name,
            author_id=author_id
        ))

    return StandardResponse(
        success=True,
        message="Filtered researches fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "researches": results
        }
    )


@router.get("/search/articles/authors", response_model=StandardResponse)
def search_articles_by_authors(
    name: str = Query(..., description="Author name to search"),
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
            if pa.article:
                articles_query.append({
                    "article": pa.article,
                    "author_name": user.name,
                    "author_id": author.id,
                    "author_order": pa.author_order
                })

    total = len(articles_query)
    start = (page - 1) * limit
    end = start + limit
    articles_query.sort(key=lambda x: x["article"].year if x["article"].year else 0, reverse=True)

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
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Query artikel dengan pencarian judul mirip (case-insensitive)
    articles_query = db.query(Article).filter(
        func.lower(Article.title).like(f"%{title.lower()}%")
    ).all()

    if not articles_query:
        raise HTTPException(status_code=404, detail="Articles not found")

    total = len(articles_query)
    start = (page - 1) * limit
    end = start + limit
    articles_query.sort(key=lambda x: x.year if x.year else 0, reverse=True)
    paginated = articles_query[start:end]

    # Untuk setiap artikel, cari author pertama (order = 1) dan semua author terkait
    articles = []
    for article in paginated:
        authorships = article.authors  # dari relasi PublicationAuthor
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


@router.get("/search/researches/authors", response_model=StandardResponse)
def search_researches_by_authors(
    name: str = Query(..., description="Author name to search"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(func.lower(User.name).like(f"%{name.lower()}%")).all()
    if not users:
        raise HTTPException(status_code=404, detail="Authors not found")

    researches_raw = []
    for user in users:
        author = user.author
        if not author:
            continue

        for ra in author.research:
            research = ra.research
            if not research:
                continue

            # Nama leader
            leader = next(
                (r.author.user.name for r in research.authors if r.is_leader and r.author and r.author.user),
                "Unknown"
            )

            # Personil
            personils = "; ".join([
                r.author.user.name for r in research.authors
                if r.author and r.author.user and not r.is_leader
            ])

            researches_raw.append({
                "research": research,
                "author_name": user.name,
                "author_id": author.id,
                "leader": leader,
                "personils": personils
            })

    total = len(researches_raw)
    start = (page - 1) * limit
    end = start + limit
    researches_raw.sort(key=lambda x: x["research"].year if x["research"].year else 0, reverse=True)
    paginated = researches_raw[start:end]

    researches = [
        ResearchResponse(
            title=item["research"].title,
            leader=item["leader"],
            jenis_penelitian=item["research"].fund_type,
            personils=item["personils"],
            year=item["research"].year,
            dana_penelitian=item["research"].fund,
            status_penelitian=item["research"].fund_status,
            sumber_pendanaan=item["research"].fund_source,
            author_name=item["author_name"],
            author_id=item["author_id"]

        )
        for item in paginated
    ]

    return StandardResponse(
        success=True,
        message=f"Researches for '{name}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "researches": researches
        }
    )


@router.get("/search/researches/title", response_model=StandardResponse)
def search_researches_by_title(
    title: str = Query(..., description="Judul penelitian yang ingin dicari"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Ambil semua research yang judulnya mirip
    matched_researches = db.query(Research).filter(
        func.lower(Research.title).like(f"%{title.lower()}%")
    ).all()

    if not matched_researches:
        raise HTTPException(status_code=404, detail="Researches not found")

    researches_raw = []
    for research in matched_researches:
        # Ambil leader
        leader = next(
            (r.author.user.name for r in research.authors if r.is_leader and r.author and r.author.user),
            "Unknown"
        )

        # Personil
        personils = "; ".join([
            r.author.user.name for r in research.authors
            if r.author and r.author.user and not r.is_leader
        ])

        # Ambil author pertama (boleh siapa saja)
        first_author = next(
            (r for r in research.authors if r.author and r.author.user),
            None
        )
        author_name = first_author.author.user.name if first_author else "Unknown"
        author_id = first_author.author.id if first_author else None

        researches_raw.append({
            "research": research,
            "author_name": author_name,
            "author_id": author_id,
            "leader": leader,
            "personils": personils
        })

    # Pagination
    total = len(researches_raw)
    start = (page - 1) * limit
    end = start + limit
    researches_raw.sort(key=lambda x: x["research"].year if x["research"].year else 0, reverse=True)
    paginated = researches_raw[start:end]

    # Format response
    researches = [
        ResearchResponse(
            title=item["research"].title,
            leader=item["leader"],
            jenis_penelitian=item["research"].fund_type,
            personils=item["personils"],
            year=item["research"].year,
            dana_penelitian=item["research"].fund,
            status_penelitian=item["research"].fund_status,
            sumber_pendanaan=item["research"].fund_source,
            author_name=item["author_name"],
            author_id=item["author_id"]
        )
        for item in paginated
    ]

    return StandardResponse(
        success=True,
        message=f"Researches with title containing '{title}' fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "researches": researches
        }
    )


