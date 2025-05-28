import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Author, PublicationAuthor
from schemas import CrawlAuthors, TopAuthorResponse

BASE_URL = "https://sinta.kemdikbud.go.id/departments/authors/20/896879FE-5FBE-4AB0-A7CD-3FAD1EEE3CFF/6635C54C-E05B-4161-A443-BCCA6926474A"

# User-Agent agar tidak terdeteksi sebagai bot
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_and_save_authors(db: Session):
    scraped_data = scrape_sinta()
    saved_count, skipped_count = save_scraped_data(scraped_data, db)
    
    return {
        "success": True,
        "message": f"Scraping selesai: {saved_count} data disimpan, {skipped_count} dilewati karena duplikat.",
        "total_scraped": len(scraped_data)
    }

def scrape_sinta():
    results = []
    for page in range(1, 8):  # Ganti sesuai kebutuhan
        url = f"{BASE_URL}?page={page}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            author_sections = soup.find_all("div", class_="au-item mt-3 mb-3 pb-5 pt-3")

            for author in author_sections:
                name_tag = author.find("a")
                name = name_tag.get_text(strip=True) if name_tag else "N/A"
                profile_link = name_tag["href"] if name_tag else "N/A"
                sinta_id_tag = author.find("div", class_="profile-id")
                sinta_id = sinta_id_tag.get_text(strip=True).replace("ID : ", "") if sinta_id_tag else "N/A"

                scopus_hindex_tag = author.find("span", class_="profile-id text-warning")
                scopus_hindex = scopus_hindex_tag.get_text(strip=True).replace("Scopus H-Index : ", "") if scopus_hindex_tag else "0"

                gs_hindex_tag = author.find("span", class_="profile-id text-success ml-3")
                gs_hindex = gs_hindex_tag.get_text(strip=True).replace("GS H-Index : ", "") if gs_hindex_tag else "0"

                score_blocks = author.find_all("div", class_="stat-num text-center")
                sinta_score_3yr = score_blocks[0].get_text(strip=True) if len(score_blocks) >= 2 else "0"
                sinta_score_total = score_blocks[1].get_text(strip=True) if len(score_blocks) >= 2 else "0"
                affil_score_3yr = score_blocks[2].get_text(strip=True) if len(score_blocks) >= 4 else "0"
                affil_score_total = score_blocks[3].get_text(strip=True) if len(score_blocks) >= 4 else "0"

                results.append(
                    CrawlAuthors(
                        lecturer_name=name,
                        sinta_profile_url=profile_link,
                        sinta_id=sinta_id,
                        profile_link=profile_link,
                        scopus_hindex=scopus_hindex,
                        gs_hindex=gs_hindex,
                        sinta_score_3yr=sinta_score_3yr,
                        sinta_score_total=sinta_score_total,
                        affil_score_3yr=affil_score_3yr,
                        affil_score_total=affil_score_total
                    )
                )
                time.sleep(1)
    return results

def get_or_create_user(db: Session, name: str):
    user = db.query(User).filter(User.name == name).first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def save_scraped_data(scraped_data: list, db: Session):
    saved = 0
    skipped = 0

    for data in scraped_data:
        user = get_or_create_user(db, data.lecturer_name)

        existing_author = db.query(Author).filter(Author.user_id == user.id).first()
        if existing_author:
            skipped += 1
            continue

        author = Author(
            user_id=user.id,
            sinta_profile_url=str(data.sinta_profile_url),
            sinta_id=str(data.sinta_id),
            scopus_hindex=str(data.scopus_hindex),
            gs_hindex=str(data.gs_hindex),
            sinta_score_3yr=str(data.sinta_score_3yr),
            sinta_score_total=str(data.sinta_score_total),
            affil_score_3yr=str(data.affil_score_3yr),
            affil_score_total=str(data.affil_score_total),
        )
        db.add(author)
        saved += 1

    db.commit()
    return saved, skipped


def get_top_authors(db: Session, limit: int = 10):
    results = (
        db.query(
            Author.id.label("author_id"),
            User.name.label("name"),
            func.count(PublicationAuthor.article_id).label("article_count")
        )
        .join(User, Author.user_id == User.id)
        .join(PublicationAuthor, PublicationAuthor.author_id == Author.id)
        .group_by(Author.id, User.name)
        .order_by(func.count(PublicationAuthor.article_id).desc())
        .limit(limit)
        .all()
    )

    top_authors = []
    for r in results:
        top_authors.append({
            "author_id": r.author_id,
            "name": r.name or "-",
            "article_count": r.article_count or 0
        })

    return {
        "success": True,
        "message": "Top authors fetched successfully",
        "data": top_authors
    }