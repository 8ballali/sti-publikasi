from typing import Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy import case
from models import Research
from schemas import ResearchResponse, StandardResponse
from fastapi import HTTPException
from sqlalchemy import func
from models import User


def get_all_researches_service(
    db: Session,
    min_year: Optional[int],
    max_year: Optional[int],
    termahal: bool,
    fund_source: Optional[Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]],
    page: int,
    limit: int
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
        leader = research.leader_name or "Unknown"

        # Hindari duplikat nama personil dan pastikan bukan leader
        personil_names = set()
        for ra in research.authors:
            if ra.author and ra.author.user:
                name = ra.author.user.name
                if name != leader:
                    personil_names.add(name)
        personils = "; ".join(sorted(personil_names))

        first_author = next(
            (ra.author for ra in research.authors if ra.author and ra.author.user),
            None
        )

        result.append(ResearchResponse(
            title=research.title,
            year=research.year,
            dana_penelitian=research.fund,
            status_penelitian=research.fund_status,
            sumber_pendanaan=research.fund_source,
            jenis_penelitian=research.fund_type,
            leader_name=leader,
            personils=personils,
            author_name=first_author.user.name if first_author else "Unknown",
            author_id=first_author.id if first_author else 0
        ))

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "researches": result
    }


def search_researches_by_authors_service(
    db: Session,
    name: str,
    min_year: Optional[int],
    max_year: Optional[int],
    fund_source: Optional[Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]],
    termahal: bool,
    page: int,
    limit: int
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

            # Leader dari field langsung
            leader = research.leader_name or "Unknown"

            # Personils (hindari duplikat dan pengecualian leader)
            personil_names = set()
            for r in research.authors:
                if r.author and r.author.user:
                    name_ = r.author.user.name
                    if name_ != leader:
                        personil_names.add(name_)
            personils = "; ".join(sorted(personil_names))

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


def search_researches_by_title_service(
    db: Session,
    title: str,
    min_year: Optional[int],
    max_year: Optional[int],
    fund_source: Optional[Literal["INTERNAL_SOURCE", "BIMA_SOURCE", "SIMLITABMAS_SOURCE"]],
    termahal: bool,
    page: int,
    limit: int
):
    query = db.query(Research).filter(
        func.lower(Research.title).like(f"%{title.lower()}%")
    )

    if min_year is not None:
        query = query.filter(Research.year >= min_year)
    if max_year is not None:
        query = query.filter(Research.year <= max_year)
    if fund_source:
        query = query.filter(Research.fund_source == fund_source)

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
        leader = research.leader_name or "Unknown"

        personil_names = set()
        for ra in research.authors:
            if ra.author and ra.author.user:
                name = ra.author.user.name
                if name != leader:
                    personil_names.add(name)
        personils = "; ".join(sorted(personil_names))

        first_author = next(
            (ra.author for ra in research.authors if ra.author and ra.author.user),
            None
        )

        researches_raw.append({
            "research": research,
            "author_name": first_author.user.name if first_author else "Unknown",
            "author_id": first_author.id if first_author else 0,
            "leader": leader,
            "personils": personils
        })

    total = len(researches_raw)
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