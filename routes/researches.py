from fastapi import APIRouter,  Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import Author, ResearcherAuthor, Research
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync
from repository.research_crawl import research_sync
import re
import pandas as pd
from models import Research, ResearcherAuthor
import io

router = APIRouter(
    tags=['Researches Data']
)


@router.post("/upload-research")
def upload_research_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = file.file.read()
        df = pd.read_csv(io.BytesIO(content))

        inserted_research = 0
        inserted_relations = 0

        for _, row in df.iterrows():
            # Ambil dan bersihkan data dari CSV
            sinta_id = str(row['User ID']).strip()
            title = str(row['Title']).strip()
            leader_name = str(row['Leader']).strip() if not pd.isna(row['Leader']) else None

            # Cek author berdasarkan SINTA ID
            author = db.query(Author).filter(Author.sinta_id == sinta_id).first()
            if not author or not author.user:
                continue

            year = int(row['Year']) if not pd.isna(row['Year']) else None
            fund = float(row['Dana Penelitian']) if not pd.isna(row['Dana Penelitian']) else None
            fund_status = row['Status Penelitian'] if not pd.isna(row['Status Penelitian']) else None
            fund_source = row['Sumber Pendanaan'].strip() if not pd.isna(row['Sumber Pendanaan']) else None
            fund_type = row['Jenis Penelitian'] if not pd.isna(row['Jenis Penelitian']) else None

            # Cek apakah research sudah ada (berdasarkan title, year, fund)
            research = db.query(Research).filter(
                Research.title == title,
                Research.year == year,
                Research.fund == fund
            ).first()

            if not research:
                research = Research(
                    title=title,
                    fund=fund,
                    fund_status=fund_status,
                    fund_source=fund_source,
                    fund_type=fund_type,
                    year=year,
                    leader_name=leader_name  # tambahkan nama leader manual jika tidak ada di DB
                )
                db.add(research)
                db.commit()
                db.refresh(research)
                inserted_research += 1

            # Cek apakah relasi author-research sudah ada
            existing_relation = db.query(ResearcherAuthor).filter_by(
                researcher_id=research.id,
                author_id=author.id
            ).first()
            if existing_relation:
                continue

            # Cek apakah author ini adalah leader
            author_name = author.user.name.strip()
            is_leader = author_name.lower() == (leader_name or "").lower()

            relation = ResearcherAuthor(
                researcher_id=research.id,
                author_id=author.id,
                is_leader=is_leader
            )
            db.add(relation)
            inserted_relations += 1

        db.commit()

        return {
            "success": True,
            "message": "Excel berhasil diproses.",
            "inserted_articles": inserted_research,
            "inserted_publication_authors": inserted_relations
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def normalize_name(name: str) -> str:
    return re.sub(r'\W+', '', name.lower().strip())

@router.post("/sync-researches")
def sync_all_researches(db: Session = Depends(get_db)):
    authors = db.query(Author).filter(Author.sinta_id.isnot(None)).all()
    total_inserted = 0
    total_relations = 0

    for author in authors:
        sinta_id = author.sinta_id
        if not sinta_id:
            continue

        print(f"🔍 Syncing for author: {author.user.name} ({sinta_id})")
        try:
            researches = research_sync(sinta_id)
        except Exception as e:
            print(f"⚠️ Gagal sync {sinta_id}: {e}")
            continue

        for res in researches:
            title = res["title"].strip()
            if not title:
                continue

            # Cek duplikasi research
            research = db.query(Research).filter(Research.title == title).first()
            if not research:
                research = Research(
                    title=title,
                    fund=float(res["fund"]) if res["fund"].replace(",", "").isdigit() else None,
                    fund_status=res["fund_status"] or None,
                    fund_source=res["fund_source"] or None,
                    fund_type=res["fund_type"] or None,
                    year=int(res["year"]) if res["year"].isdigit() else None
                )
                db.add(research)
                db.commit()
                db.refresh(research)
                total_inserted += 1

            # Cek relasi
            existing_relation = db.query(ResearcherAuthor).filter_by(
                researcher_id=research.id,
                author_id=author.id
            ).first()
            if existing_relation:
                continue

            # Cek apakah leader berdasarkan perbandingan nama
            author_name = normalize_name(author.user.name)
            leader_name = normalize_name(res["leader"])
            is_leader = author_name == leader_name

            researcher_author = ResearcherAuthor(
                researcher_id=research.id,
                author_id=author.id,
                is_leader=is_leader
            )
            db.add(researcher_author)
            db.commit()
            total_relations += 1

    return {
        "success": True,
        "inserted_researches": total_inserted,
        "inserted_relations": total_relations
    }