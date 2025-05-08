# services/sinta_scraper.py
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from models import User, Author, Research, ResearcherAuthor
import re

def scrape_sinta_research(db: Session):
    results = []
    lecturers = db.query(User.name, Author.sinta_profile_url, Author.id).select_from(User).join(Author).all()
    print(f"👩‍🏫 Total dosen ditemukan: {len(lecturers)}")

    for idx, (lecturer_name, profile_link, current_author_id) in enumerate(lecturers, start=1):
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

                # Cek apakah judul sudah ada
                existing_research = db.query(Research).filter(Research.title == title).first()
                if existing_research:
                    print(f"⚠️ Judul '{title}' sudah ada, lewati...")
                    continue

                first_meta_div = item.find('div', class_='ar-meta')
                leader_tag = first_meta_div.find('a', href='#!', string=lambda t: t and "Leader" in t)
                leader_name = leader_tag.text.replace('Leader : ', '').strip() if leader_tag else 'N/A'

                jenis_penelitian_tag = first_meta_div.find('a', class_='ar-pub')
                jenis_penelitian = jenis_penelitian_tag.text.strip() if jenis_penelitian_tag else 'N/A'

                all_meta_divs = item.find_all('div', class_='ar-meta')
                second_meta_div = all_meta_divs[1] if len(all_meta_divs) > 1 else None
                third_meta_div = all_meta_divs[2] if len(all_meta_divs) > 2 else None

                personil_names = []
                if second_meta_div:
                    personil_tags = second_meta_div.find_all('a', href=True)
                    personil_names = list(dict.fromkeys([
                        p.text.strip() for p in personil_tags if '/authors/profile/' in p['href']
                    ]))

                year, dana_penelitian, status_penelitian, sumber_pendanaan = None, None, None, None
                if third_meta_div:
                    year_tag = third_meta_div.find('a', class_='ar-year')
                    year_text = year_tag.text.strip() if year_tag else None
                    if year_text and year_text.isdigit():
                        year = int(year_text)

                    dana_tag = third_meta_div.find('a', class_='ar-quartile')
                    dana_str = dana_tag.text.strip().replace("Rp.", "").replace(".", "").strip() if dana_tag else None
                    dana_penelitian = float(dana_str) if dana_str and dana_str.isdigit() else None

                    status_tag = third_meta_div.find('a', class_='ar-quartile text-success')
                    status_penelitian = status_tag.text.strip() if status_tag else None

                    sumber_tag = third_meta_div.find('a', class_='ar-quartile text-info')
                    sumber_pendanaan = sumber_tag.text.strip() if sumber_tag else None

                # Buat research
                research = Research(
                    title=title,
                    fund=dana_penelitian,
                    fund_status=status_penelitian,
                    fund_source=sumber_pendanaan,
                    fund_type=jenis_penelitian,
                    year=year
                )
                db.add(research)
                db.commit()
                db.refresh(research)

                # Gabungkan leader dan personil, lalu cari di DB
                all_names = set(personil_names + [leader_name])
                for name in all_names:
                    author = db.query(Author).join(User).filter(User.name.ilike(f"%{name}%")).first()
                    if not author:
                        print(f"🔍 Author '{name}' tidak ditemukan di database.")
                        continue

                    is_leader_flag = name.lower() in leader_name.lower()

                    # Hindari duplikat insert
                    existing_link = db.query(ResearcherAuthor).filter_by(
                        researcher_id=research.id,
                        author_id=author.id
                    ).first()

                    if not existing_link:
                        db.add(ResearcherAuthor(
                            researcher_id=research.id,
                            author_id=author.id,
                            is_leader=is_leader_flag
                        ))

                db.commit()

                results.append({
                    "User": profile_link,
                    "Title": title,
                    "Leader": leader_name,
                    "Jenis Penelitian": jenis_penelitian,
                    "Personils": list(all_names),
                    "Year": year,
                    "Dana Penelitian": dana_penelitian,
                    "Status Pendanaan": status_penelitian,
                    "Sumber Pendanaan": sumber_pendanaan
                })

            except Exception as e:
                print(f"⚠️ Gagal memproses item: {e}")
                continue

        time.sleep(1)

    return results
