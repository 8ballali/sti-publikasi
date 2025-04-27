from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data, scrape_subjects_from_profile
from models import User, Author, Subject, UserSubject


router = APIRouter()

router = APIRouter(
    tags=['Authors']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping Authors selesai dan data telah disimpan ke database!"}

@router.get("/scrape/subjects")
async def scrape_subjects(db: Session = Depends(get_db)):
    # Ambil semua author dari database
    authors = db.query(Author).all()

    results = []
    for author in authors:
        user = db.query(User).filter(User.id == author.user_id).first()
        lecturer_name = user.name if user else "N/A"

        subjects = scrape_subjects_from_profile(author.sinta_profile_url)

        for subject_name in subjects:
            # Cek apakah subject sudah ada
            subject = db.query(Subject).filter(Subject.name == subject_name).first()
            if not subject:
                # Kalau belum ada, buat baru
                subject = Subject(name=subject_name)
                db.add(subject)
                db.commit()
                db.refresh(subject)

            # Cek apakah relasi author-subject sudah ada
            user_subject = db.query(UserSubject).filter_by(
                author_id=author.id, subject_id=subject.id
            ).first()
            if not user_subject:
                # Kalau belum ada, buat baru
                user_subject = UserSubject(author_id=author.id, subject_id=subject.id)
                db.add(user_subject)
                db.commit()

        results.append({
            "lecturer_name": lecturer_name,
            "sinta_profile_url": author.sinta_profile_url,
            "sinta_score_3yr": author.sinta_score_3yr,
            "sinta_score_total": author.sinta_score_total,
            "affil_score_3yr": author.affil_score_3yr,
            "affil_score_total": author.affil_score_total,
            "subjects": subjects  
        })

    return {"scraped_results": results}


@router.get("/scrape/authors/debug")
async def scrape_authors_debug():
    scraped_data = scrape_sinta()

    # Ubah hasil scraping ke bentuk dictionary agar bisa dikembalikan dalam JSON
    debug_results = []
    for data in scraped_data:
        debug_results.append({
            "lecturer_name": data.lecturer_name,
            "sinta_profile_url": data.sinta_profile_url,
            "sinta_id": data.sinta_id,
            "profile_link": data.profile_link,
            "sinta_score_3yr": data.sinta_score_3yr,
            "sinta_score_total": data.sinta_score_total,
            "affil_score_3yr": data.affil_score_3yr,
            "affil_score_total": data.affil_score_total
        })

    return {"scraped_results": debug_results}