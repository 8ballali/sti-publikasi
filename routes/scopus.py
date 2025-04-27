from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author
from repository.scopus_abstract_crawl import scopus_scrapping,scopus_data, scopus_sync
from bs4 import BeautifulSoup
import requests
import re



router = APIRouter()

router = APIRouter(
    tags=['Scopus']
)


@router.get("/scrape/scopus")
async def scrape_scopus(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scopus_scrapping(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scopus_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scopus selesai dan data telah disimpan ke database!"}


@router.get("/sync/scopus")
async def sync_scopus(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scopus_sync(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scopus_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Scraping Scopus selesai dan data telah disimpan ke database!"}


@router.get("/scrape/scopus/debug")
async def scrape_scopus_debug(db: Session = Depends(get_db)):
    results = []

    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen ditemukan: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if not profile_link:
            continue

        scopus_url = f"{profile_link}?view=scopus"
        print(f"\n📚 Memproses (SCOPUS): {lecturer_name}")
        print(f"🔗 Fetching from: {scopus_url}")

        try:
            response = requests.get(scopus_url, timeout=10)
        except Exception as e:
            print(f"❌ Error saat mengambil halaman: {e}")
            continue

        if response.status_code != 200:
            print(f"❌ Gagal mengambil data dari {scopus_url}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('div', class_='ar-list-item mb-5')

        for item in articles:
            try:
                # Judul publikasi
                title_tag = item.find('div', class_='ar-title').find('a')
                title = title_tag.text.strip() if title_tag else 'N/A'

                # Akreditasi
                accred_tag = item.find('div', class_='ar-meta').find('a', href='#!')
                accred = accred_tag.text.strip() if accred_tag else 'N/A'

                # Nama jurnal
                jurnal_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
                jurnal = jurnal_tag.text.strip() if jurnal_tag else 'N/A'

                # Meta pertama
                first_meta_div = item.find('div', class_='ar-meta')

                # Author Order
                author_order_tag = first_meta_div.find('a', href="#!", text=lambda t: t and "Author Order" in t)
                if author_order_tag:
                    author_order_text = author_order_tag.text.replace('Author Order : ', '').strip()
                    match = re.match(r"(\d+)", author_order_text)
                    author_order = int(match.group(1)) if match else None
                else:
                    author_order = None

                # Creator
                creator_tag = first_meta_div.find('a', href="#!", text=lambda t: t and "Creator" in t)
                creator = creator_tag.text.replace('Creator : ', '').strip() if creator_tag else 'N/A'

                # Meta kedua
                all_meta_divs = item.find_all('div', class_='ar-meta')
                second_meta_div = all_meta_divs[1] if len(all_meta_divs) > 1 else None

                year = cited = 'N/A'
                if second_meta_div:
                    year_tag = second_meta_div.find('a', class_='ar-year')
                    year = year_tag.text.strip() if year_tag else 'N/A'

                    cited_tag = second_meta_div.find('a', class_='ar-cited')
                    cited = cited_tag.text.strip() if cited_tag else '0'

                results.append({
                    "user": lecturer_name,
                    "title": title,
                    "accred": accred,
                    "jurnal": jurnal,
                    "author_order": author_order,
                    "creator": creator,
                    "year": year,
                    "cited": cited,
                })

            except Exception as e:
                print(f"⚠️ Gagal memproses satu publikasi: {e}")
                continue

    return {"scraped_results": results}