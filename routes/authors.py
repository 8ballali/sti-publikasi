from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, scrape_and_save_authors, get_top_authors
from models import User, Author, Subject, UserSubject
from repository.subject_crawl import scrape_all_subjects
from schemas import TopAuthorResponse

import pandas as pd
from io import StringIO, BytesIO


router = APIRouter()

router = APIRouter(
    tags=['Authors & Subjects']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):

    result = scrape_and_save_authors(db)
    return result

@router.get("/scrape/subjects")
async def scrape_subjects(db: Session = Depends(get_db)):
    return scrape_all_subjects(db)

@router.get("/authors/top")
def top_authors(limit: int = 10, db: Session = Depends(get_db)):
    return get_top_authors(db, limit)


@router.post("/upload/authors")
async def upload_sinta_authors(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="File harus berformat .xls/.xlsx/.csv")

    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {str(e)}")

    inserted = 0
    updated = 0

    for _, row in df.iterrows():
        name = str(row.get("Lecturer Name", "")).strip()
        if not name:
            continue

        raw_npp = row.get("npp", None)
        npp = str(raw_npp).strip() if pd.notna(raw_npp) else None

        sinta_id = str(row.get("Sinta ID", "")).strip()
        profile_link = str(row.get("Profile Link", "")).strip()
        department = str(row.get("Department", "")).strip()

        # ambil nilai-nilai skor
        scopus_hindex = str(row.get("Scopus H-Index", "0")).strip()
        gs_hindex = str(row.get("GS H-Index", "0")).strip()
        sinta_score_3yr = str(row.get("Sinta Score 3yr", "0")).strip()
        sinta_score_total = str(row.get("Sinta Score Total", "0")).strip()
        affil_score_3yr = str(row.get("Affil Score 3yr", "0")).strip()
        affil_score_total = str(row.get("Affil Score Total", "0")).strip()

        # 1. Cek User berdasarkan nama
        user = db.query(User).filter(User.name == name).first()
        if not user:
            user = User(name=name, npp=npp)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if npp:  # hanya update jika npp ada
                user.npp = npp
                db.commit()

        # 2. Cek apakah Author sudah ada berdasarkan user_id
        author = db.query(Author).filter(Author.user_id == user.id).first()

        if author:
            # Update
            author.sinta_profile_url = profile_link
            author.sinta_id = sinta_id
            author.department = department
            author.scopus_hindex = scopus_hindex
            author.gs_hindex = gs_hindex
            author.sinta_score_3yr = sinta_score_3yr
            author.sinta_score_total = sinta_score_total
            author.affil_score_3yr = affil_score_3yr
            author.affil_score_total = affil_score_total
            updated += 1
        else:
            # Insert baru
            new_author = Author(
                user_id=user.id,
                sinta_profile_url=profile_link,
                sinta_id=sinta_id,
                department=department,
                scopus_hindex=scopus_hindex,
                gs_hindex=gs_hindex,
                sinta_score_3yr=sinta_score_3yr,
                sinta_score_total=sinta_score_total,
                affil_score_3yr=affil_score_3yr,
                affil_score_total=affil_score_total
            )
            db.add(new_author)
            inserted += 1

        db.commit()

    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "message": f"{inserted} author baru ditambahkan, {updated} author diperbarui."
    }
