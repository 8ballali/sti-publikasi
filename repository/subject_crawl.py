from sqlalchemy.orm import Session
from models import Author, User, Subject, UserSubject
import requests
from bs4 import BeautifulSoup


# User-Agent agar tidak terdeteksi sebagai bot
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_all_subjects(db: Session):
    authors = db.query(Author).all()
    results = []

    for author in authors:
        lecturer_name = get_lecturer_name(db, author.user_id)
        subjects = scrape_subjects_from_profile(author.sinta_profile_url)

        for subject_name in subjects:
            subject = get_or_create_subject(db, subject_name)
            create_user_subject_relation(db, author.id, subject.id)

        results.append({
            "lecturer_name": lecturer_name,
            "sinta_profile_url": author.sinta_profile_url,
            "sinta_id": author.sinta_id,
            "scopus_hindex": author.scopus_hindex,
            "gs_hindex": author.gs_hindex,
            "sinta_score_3yr": author.sinta_score_3yr,
            "sinta_score_total": author.sinta_score_total,
            "affil_score_3yr": author.affil_score_3yr,
            "affil_score_total": author.affil_score_total,
            "subjects": subjects
        })

    return {
        "success": True,
        "message": "Scraping selesai",
        "scraped_results": results
    }


def get_lecturer_name(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else "N/A"

def get_or_create_subject(db: Session, name: str) -> Subject:
    subject = db.query(Subject).filter_by(name=name).first()
    if not subject:
        subject = Subject(name=name)
        db.add(subject)
        db.commit()
        db.refresh(subject)
    return subject

def create_user_subject_relation(db: Session, author_id: int, subject_id: int):
    user_subject = db.query(UserSubject).filter_by(
        author_id=author_id, subject_id=subject_id
    ).first()
    if not user_subject:
        user_subject = UserSubject(author_id=author_id, subject_id=subject_id)
        db.add(user_subject)
        db.commit()


def scrape_subjects_from_profile(profile_url: str):
    if not profile_url:
        return []

    # Cek apakah url sudah lengkap
    if not profile_url.startswith("http"):
        profile_url = "https://sinta.kemdikbud.go.id" + profile_url

    response = requests.get(profile_url, headers=HEADERS)

    subjects = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        subject_list_div = soup.find("div", class_="profile-subject mt-3")
        if subject_list_div:
            subjects = [a.get_text(strip=True) for a in subject_list_div.find_all("a")]

    return subjects