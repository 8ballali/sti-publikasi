from fastapi import APIRouter,  Depends, HTTPException, UploadFile, File, BackgroundTasks
import csv
from io import StringIO
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author, ResearcherAuthor, Research
from bs4 import BeautifulSoup
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync
from repository.research_crawl import scrape_sinta_research
import re
import requests
import time
import pandas as pd
from io import BytesIO
from models import Research, ResearcherAuthor
import io
from repository import crud







router = APIRouter(
    tags=['Researches']
)


@router.post("/upload-research")
def upload_research_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = file.file.read()
        df = pd.read_csv(io.BytesIO(content))

        inserted_research = 0
        inserted_relations = 0

        for _, row in df.iterrows():
            sinta_id = str(row['User ID']).strip()
            title = str(row['Title']).strip()

            # Cek apakah author ada
            author = db.query(Author).filter(Author.sinta_id == sinta_id).first()
            if not author:
                continue

            # Cek apakah research sudah ada
            research = db.query(Research).filter(Research.title == title).first()
            if not research:
                research = Research(
                    title=title,
                    fund=float(row['Dana Penelitian']) if not pd.isna(row['Dana Penelitian']) else None,
                    fund_status=row['Status Penelitian'],
                    fund_source=row['Sumber Pendanaan'],
                    fund_type=row['Jenis Penelitian'],
                    year=int(row['Year']) if not pd.isna(row['Year']) else None
                )
                db.add(research)
                db.commit()
                db.refresh(research)
                inserted_research += 1

            # Cek duplikasi kombinasi research_id + author_id
            existing_relation = db.query(ResearcherAuthor).filter_by(
                researcher_id=research.id,
                author_id=author.id
            ).first()

            if existing_relation:
                continue

            # Cek apakah leader
            is_leader = str(row['Leader']).strip().lower() in ['ya', 'yes', '1', 'true']

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
    


# --- Fungsi Pembantu untuk Background Task (PENTING!) ---
def process_scrape_researches_for_user(user_id: str, sinta_profile_url: str):
    """
    Fungsi wrapper untuk menjalankan scraping dalam background task.
    Ia akan membuat sesi DB-nya sendiri.
    """
    db = SessionLocal() # Membuat sesi database baru
    try:
        scrape_researches_for_user_headless(user_id, sinta_profile_url, db)
    except Exception as e:
        print(f"ERROR in background task for user {user_id}: {e}")
    finally:
        db.close() # Pastikan sesi ditutup setelah selesai

# --- Fungsi Scraping Research (Headless) ---
def scrape_researches_for_user_headless(user_id: str, sinta_profile_url: str, db: Session):
    """
    Melakukan scraping data penelitian (researches) dari profil Sinta seorang user
    secara headless menggunakan requests dan BeautifulSoup, lalu menyimpannya ke database.
    """
    page = 1

    # Dapatkan objek Author berdasarkan sinta_id sebelum loop scraping
    db_author = crud.get_author_by_sinta_id(db, user_id)
    if not db_author:
        db_author = crud.create_author(db, user_id, sinta_profile_url)
        print(f"INFO: Author dengan Sinta ID {user_id} belum ada di DB, membuat baru.")

    while True:
        url = f'{sinta_profile_url}?page={page}&view=researches'
        print(f"Fetching page: {url} for user {user_id}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url} for user {user_id}: {e}")
            break

        items = soup.find_all("div", class_="ar-list-item mb-5")
        if not items:
            print(f"✓ Tidak ada data lagi di page {page} untuk user {user_id}")
            break

        for item in items:
            try:
                title = 'N/A'
                leader = 'N/A'
                jenis_penelitian = 'N/A'
                personils_str = 'N/A'
                year = None
                dana = 'N/A'
                status = 'N/A'
                sumber = 'N/A'

                title_tag = item.find("div", class_="ar-title")
                if title_tag:
                    title_a = title_tag.find("a")
                    if title_a:
                        title = title_a.text.strip()

                existing_research = crud.get_research_by_title(db, title)
                if existing_research:
                    existing_researcher_author = crud.get_researcher_author(db, existing_research.id, db_author.id)
                    if existing_researcher_author:
                        print(f"SKIP: Penelitian '{title}' sudah ada di database untuk penulis {user_id}.")
                        continue

                meta_divs = item.find_all("div", class_="ar-meta")

                if len(meta_divs) > 0:
                    first_meta = meta_divs[0]
                    spans = first_meta.find_all("a")
                    for span in spans:
                        text = span.text.strip()
                        if "Leader :" in text:
                            leader = text.replace("Leader :", "").strip()
                        elif "ar-pub" in span.get("class", []):
                            jenis_penelitian = text

                all_personil_sinta_ids = []
                if len(meta_divs) > 1:
                    second_meta = meta_divs[1]
                    personil_tags = second_meta.find_all("a")
                    personils = []
                    for p_tag in personil_tags:
                        text = p_tag.text.strip()
                        if "Personils" not in text:
                            personils.append(text)
                            href = p_tag.get("href")
                            if href and "authors/profile/" in href:
                                try:
                                    sinta_id_from_url = href.split('/')[-1]
                                    if sinta_id_from_url and sinta_id_from_url not in all_personil_sinta_ids:
                                        all_personil_sinta_ids.append(sinta_id_from_url)
                                except:
                                    pass

                    personils_str = ', '.join(personils) if personils else 'N/A'

                if len(meta_divs) > 2:
                    third_meta = meta_divs[2]
                    third_a_tags = third_meta.find_all("a")
                    for a in third_a_tags:
                        text = a.text.strip()
                        class_attr = a.get("class", [])

                        if "ar-year" in class_attr:
                            try:
                                year = int(text)
                            except ValueError:
                                year = None
                        elif "text-success" in class_attr and "ar-quartile" in class_attr:
                            status = text
                        elif "text-info" in class_attr and "ar-quartile" in class_attr:
                            sumber = text
                        elif "ar-quartile" in class_attr and "text" not in class_attr:
                            raw_dana = text.replace("Rp", "").replace(".", "").replace(" ", "").strip()
                            dana = raw_dana

                research_data = {
                    "title": title,
                    "jenis_penelitian": jenis_penelitian,
                    "year": year,
                    "dana": dana,
                    "status": status,
                    "sumber": sumber
                }

                db_research = crud.get_research_by_title(db, title)
                if not db_research:
                    db_research = crud.create_research(db, research_data)
                    db.flush()
                    print(f"✓ Penelitian '{title[:60]}...' berhasil ditambahkan.")
                else:
                    print(f"INFO: Penelitian '{title[:60]}...' sudah ada di database.")

                for sinta_id_personil in all_personil_sinta_ids:
                    current_personil_db_author = crud.get_author_by_sinta_id(db, sinta_id_personil)
                    if not current_personil_db_author:
                        current_personil_db_author = crud.create_author(db, sinta_id_personil, f"https://sinta.kemdikbud.go.id/authors/profile/{sinta_id_personil}")
                        print(f"INFO: Personil dengan Sinta ID {sinta_id_personil} belum ada di DB, membuat baru.")

                    is_current_leader = (sinta_id_personil == user_id)

                    existing_ra = crud.get_researcher_author(db, db_research.id, current_personil_db_author.id)
                    if not existing_ra:
                        crud.add_researcher_to_research(db, db_research.id, current_personil_db_author.id, is_current_leader)
                        print(f"✓ Menambahkan peneliti {sinta_id_personil} ke penelitian '{title[:60]}...'.")
                    else:
                        print(f"INFO: Peneliti {sinta_id_personil} sudah terhubung dengan penelitian '{title[:60]}...'.")

                db.commit()

            except Exception as e:
                db.rollback()
                print(f"Error parsing item for user {user_id}: {e}")

        page += 1
        time.sleep(1.5)

@router.post("/sync-researches/")
async def sync_all_researches(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Endpoint untuk memulai sinkronisasi data penelitian (Research) dari Sinta ke database.
    Proses scraping akan berjalan di background secara headless.
    """
    
    # Ambil semua penulis dari database
    authors_from_db = crud.get_all_authors(db)

    if not authors_from_db:
        print("Tidak ada penulis di database. Mencoba membaca dari sinta_authors.csv sebagai daftar awal.")
        try:
            with open("sinta_authors.csv", mode='r', encoding='utf-8') as sinta_file:
                reader = csv.DictReader(sinta_file)
                for row in reader:
                    sinta_id = row['Sinta ID']
                    sinta_profile_url = row.get('sinta_profile_url', f'https://sinta.kemdikbud.go.id/authors/profile/{sinta_id}')
                    
                    # Tambahkan ke DB jika belum ada
                    existing_author = crud.get_author_by_sinta_id(db, sinta_id)
                    if not existing_author:
                        crud.create_author(db, sinta_id, sinta_profile_url)
                        print(f"Menambahkan Sinta ID {sinta_id} dari CSV ke database.")
                db.commit() # Commit setelah semua author dari CSV ditambahkan
            # Setelah menambahkan dari CSV, ambil lagi dari DB untuk memastikan semua terdaftar
            authors_from_db = crud.get_all_authors(db)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="sinta_authors.csv not found and no authors in database.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading sinta_authors.csv: {e}")

    if not authors_from_db:
        raise HTTPException(status_code=404, detail="No authors found to scrape for researches.")

    # Jalankan scraping di background untuk setiap penulis
    for author in authors_from_db:
        # Gunakan fungsi scraping headless yang baru
        background_tasks.add_task(scrape_researches_for_user_headless, author.sinta_id, author.sinta_profile_url, db)
    
    return {"message": "Sinkronisasi data penelitian (Research) dimulai di background secara headless. Lihat log server untuk progres."}