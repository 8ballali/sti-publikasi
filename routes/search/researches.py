from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import AuthorDetailResponse, ArticleResponse, ResearchResponse
from repository.author_crawl import get_top_authors
from typing import Optional, Literal
from models import Author,User, PublicationAuthor, Article, Research
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import func, case
from schemas import StandardResponse
from fastapi import Query


router = APIRouter(
    tags=['Researches Search']
)

def paginate_query(query, page: int, limit: int):
    return query.offset((page - 1) * limit).limit(limit).all()


@router.get("/researches", response_model=StandardResponse)
def get_all_researches(
    min_year: Optional[int] = Query(None, description="Tahun minimal"),
    max_year: Optional[int] = Query(None, description="Tahun maksimal"),
    termahal: bool = Query(False, description="Urutkan berdasarkan dana terbanyak"),
    fund_source: Optional[
        Literal["INTERNAL SOURCE", "BIMA SOURCE", "SIMLITABMAS SOURCE"]
    ] = Query(None, description="Sumber dana penelitian"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Research)

    if min_year is not None:
        query = query.filter(Research.year >= min_year)
    if max_year is not None:
        query = query.filter(Research.year <= max_year)

    if fund_source:
        query = query.filter(Research.fund_source == fund_source)

    # Sorting
    if termahal:
        query = query.order_by(
            case((Research.fund == None, 1), else_=0),
            Research.fund.desc()
        )
    else:
        query = query.order_by(
            case((Research.year == None, 1), else_=0),
            Research.year.desc()
        )

    total = query.count()
    researches_list = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for research in researches_list:
        leader = next(
            (r.author.user.name for r in research.authors if r.is_leader and r.author and r.author.user),
            "Unknown"
        )
        personils = "; ".join([
            r.author.user.name for r in research.authors
            if r.author and r.author.user and not r.is_leader
        ])
        first_author = next(
            (r.author for r in research.authors if r.author and r.author.user),
            None
        )

        result.append(ResearchResponse(
            title=research.title,
            year=research.year,
            dana_penelitian=research.fund,
            status_penelitian=research.fund_status,
            sumber_pendanaan=research.fund_source,
            jenis_penelitian=research.fund_type,
            leader=leader,
            personils=personils,
            author_name=first_author.user.name if first_author else "Unknown",
            author_id=first_author.id if first_author else 0,
            leader_name=research.leader_name
        ))

    return StandardResponse(
        success=True,
        message="Daftar penelitian berhasil diambil.",
        data={
            "page": page,
            "limit": limit,
            "total": total,
            "researches": result
        }
    )

@router.get("/search/researches/authors", response_model=StandardResponse)
def search_researches_by_authors(
    name: str = Query(..., description="Author name to search"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    fund_source: Optional[
        Literal["INTERNAL SOURCE", "BIMA SOURCE", "SIMLITABMAS SOURCE"]
    ] = Query(None, description="Filter by fund source"),
    termahal: bool = Query(False, description="Sort by highest fund"),
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

            # Filter tahun
            if min_year is not None and (not research.year or research.year < min_year):
                continue
            if max_year is not None and (not research.year or research.year > max_year):
                continue

            # Filter fund source
            if fund_source and research.fund_source != fund_source:
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
    
    # Sorting
    if termahal:
        researches_raw.sort(
            key=lambda x: x["research"].fund if x["research"].fund is not None else -1,
            reverse=True
        )
    else:
        researches_raw.sort(
            key=lambda x: x["research"].year if x["research"].year else 0,
            reverse=True
        )

    # Pagination
    start = (page - 1) * limit
    end = start + limit
    paginated = researches_raw[start:end]

    researches = [
        ResearchResponse(
            title=item["research"].title,
            jenis_penelitian=item["research"].fund_type,
            personils=item["personils"],
            year=item["research"].year,
            dana_penelitian=item["research"].fund,
            status_penelitian=item["research"].fund_status,
            sumber_pendanaan=item["research"].fund_source,
            author_name=item["author_name"],
            author_id=item["author_id"],
            leader_name=item["leader"],
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
    min_year: Optional[int] = Query(None, description="Tahun minimal"),
    max_year: Optional[int] = Query(None, description="Tahun maksimal"),
    fund_source: Optional[
        Literal["INTERNAL SOURCE", "BIMA SOURCE", "SIMLITABMAS SOURCE"]
    ] = Query(None, description="Filter berdasarkan sumber pendanaan"),
    termahal: bool = Query(False, description="Urutkan berdasarkan dana terbanyak"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Query awal
    query = db.query(Research).filter(
        func.lower(Research.title).like(f"%{title.lower()}%")
    )

    # Filter tahun
    if min_year is not None:
        query = query.filter(Research.year >= min_year)
    if max_year is not None:
        query = query.filter(Research.year <= max_year)

    # Filter sumber dana
    if fund_source:
        query = query.filter(Research.fund_source == fund_source)

    # Sorting
    if termahal:
        query = query.order_by(
            case((Research.fund == None, 1), else_=0),
            Research.fund.desc()
        )
    else:
        query = query.order_by(
            case((Research.year == None, 1), else_=0),
            Research.year.desc()
        )

    matched_researches = query.all()

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

        # Ambil author pertama
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
    paginated = researches_raw[start:end]

    # Format response
    researches = [
        ResearchResponse(
            title=item["research"].title,
            jenis_penelitian=item["research"].fund_type,
            personils=item["personils"],
            year=item["research"].year,
            dana_penelitian=item["research"].fund,
            status_penelitian=item["research"].fund_status,
            sumber_pendanaan=item["research"].fund_source,
            author_name=item["author_name"],
            author_id=item["author_id"],
            leader_name=item["leader"]
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

