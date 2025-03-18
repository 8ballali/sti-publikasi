import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy.orm import Session
from models import User, Author
from schemas import CrawlAuthors

BASE_URL = "https://sinta.kemdikbud.go.id/departments/authors/20/896879FE-5FBE-4AB0-A7CD-3FAD1EEE3CFF/6635C54C-E05B-4161-A443-BCCA6926474A"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_sinta():
    results = []
    for page in range(1, 8):  # Scrape 2 halaman pertama
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
                        sinta_score_3yr=sinta_score_3yr,
                        sinta_score_total=sinta_score_total,
                        affil_score_3yr=affil_score_3yr,
                        affil_score_total=affil_score_total
                    )
                )
                time.sleep(1)

    return results


def save_scraped_data(scraped_data: list[CrawlAuthors], db: Session):
    for data in scraped_data:
        # Cek apakah user sudah ada di database berdasarkan nama
        user = db.query(User).filter(User.name == data.lecturer_name).first()

        if not user:
            # Jika belum ada, buat user baru
            user = User(name=data.lecturer_name)
            db.add(user)
            db.commit()  # Memastikan user.id tersedia sebelum digunakan
            db.refresh(user)

        # Cek apakah author dengan user_id sudah ada
        existing_author = db.query(Author).filter(
            Author.user_id == user.id,
            Author.sinta_profile_url == str(data.sinta_profile_url)
        ).first()

        if not existing_author:
            # Jika belum ada, tambahkan data author baru
            author = Author(
                user_id=user.id,
                sinta_profile_url=str(data.sinta_profile_url),
                sinta_score_3yr=int(data.sinta_score_3yr) if data.sinta_score_3yr.isdigit() else None,
                sinta_score_total=int(data.sinta_score_total) if data.sinta_score_total.isdigit() else None,
                affil_score_3yr=int(data.affil_score_3yr) if data.affil_score_3yr.isdigit() else None,
                affil_score_total=int(data.affil_score_total) if data.affil_score_total.isdigit() else None,
            )
            db.add(author)

    db.commit()