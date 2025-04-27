from fastapi import APIRouter,  Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author
from bs4 import BeautifulSoup
import requests, time
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync



router = APIRouter()

router = APIRouter(
    tags=['Researches']
)


@router.get("/scrape/research/sinta/debug")
async def scrape_research_sinta_debug(db: Session = Depends(get_db)):
    results = []

    # Ambil dosen yang punya link profil SINTA
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"👩‍🏫 Total dosen ditemukan: {len(lecturers)}")

    for idx, (lecturer_name, profile_link) in enumerate(lecturers, start=1):
        if not profile_link:
            continue

        research_url = f"{profile_link}?view=researches"
        print(f"\n[{idx}/{len(lecturers)}] 📄 Memproses: {lecturer_name}")
        print(f"🔗 URL: {research_url}")
        try:
            response = requests.get(research_url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Gagal akses halaman: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='ar-list-item mb-5')

        for item in items:
            try:
                title_tag = item.find('div', class_='ar-title').find('a')
                title = title_tag.text.strip() if title_tag else 'N/A'

                first_meta_div = item.find('div', class_='ar-meta')
                leader_tag = first_meta_div.find('a', href='#!', string=lambda t: t and "Leader" in t)
                leader = leader_tag.text.replace('Leader : ', '').strip() if leader_tag else 'N/A'

                jenis_penelitian_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
                jenis_penelitian = jenis_penelitian_tag.text.strip() if jenis_penelitian_tag else 'N/A'

                all_meta_divs = item.find_all('div', class_='ar-meta')
                second_meta_div = all_meta_divs[1] if len(all_meta_divs) > 1 else None
                third_meta_div = all_meta_divs[2] if len(all_meta_divs) > 2 else None

                personils = 'N/A'
                if second_meta_div:
                    personil_tags = second_meta_div.find_all('a', href=True)
                    personils_raw = [p.text.strip() for p in personil_tags if '/authors/profile/' in p['href']]
                    personils_clean = ', '.join(dict.fromkeys(personils_raw)) if personils_raw else 'N/A'
                    personils = personils_clean

                year = dana_penelitian = status_penelitian = sumber_pendanaan = 'N/A'
                if third_meta_div:
                    year_tag = third_meta_div.find('a', class_='ar-year')
                    year_text = year_tag.text.strip() if year_tag else 'N/A'
                    year = str(year_text) if year_text.isdigit() else 'N/A'

                    dana_tag = third_meta_div.find('a', class_='ar-quartile')
                    dana_penelitian = dana_tag.text.strip() if dana_tag else 'N/A'

                    status_tag = third_meta_div.find('a', class_='ar-quartile text-success')
                    status_penelitian = status_tag.text.strip() if status_tag else 'N/A'

                    sumber_tag = third_meta_div.find('a', class_='ar-quartile text-info')
                    sumber_pendanaan = sumber_tag.text.strip() if sumber_tag else 'N/A'

                result_item = {
                    "User": f"{profile_link}?view=researches",
                    "Title": title,
                    "Leader": leader,
                    "Jenis Penelitian": jenis_penelitian,
                    "Personils": personils,
                    "Year": year,
                    "Dana Penelitian": dana_penelitian,
                    "Status Pendanaan": status_penelitian,
                    "Sumber Pendanaan": sumber_pendanaan
                }

                results.append(result_item)

            except Exception as e:
                print(f"⚠️ Gagal memproses 1 item: {e}")
                continue

        time.sleep(1)  # delay biar nggak dibanned

    return {"scraped_researches": results}

@router.get("/scrape/researches")
async def scrape_researches(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scholar_scrapping(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scholar_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scholar selesai dan data telah disimpan ke database!"}


