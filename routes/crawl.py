from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from repository.author_crawl import scrape_sinta, save_scraped_data
from repository.scholar_abstract_crawl import scholar_scrapping,scholar_data, scholar_sync
from models import User, Author, Article
from schemas import GarudaAbstractResponse
from typing import List
from repository.garuda_abstract_crawl import garuda_data,garuda_scrapping, garuda_sync, garuda_abstract_scraping
from repository.scopus_abstract_crawl import scopus_scrapping,scopus_data, scopus_sync
from fastapi.encoders import jsonable_encoder
from bs4 import BeautifulSoup
import requests, time
import re
from sqlalchemy.exc import SQLAlchemyError



router = APIRouter()

router = APIRouter(
    tags=['CRAWL']
)

@router.get("/scrape/authors")
async def scrape_authors(db: Session = Depends(get_db)):
    scraped_data = scrape_sinta()
    save_scraped_data(scraped_data, db)
    return {"message": "Scraping Authors selesai dan data telah disimpan ke database!"}

@router.get("/scrape/garuda")
async def scrape_garuda(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            
            
            scraped_data = garuda_scrapping(lecturer_name, profile_link)
            
            print(f"Scraped data untuk {lecturer_name}: {scraped_data}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")  # Debugging
            
            # Simpan hasil scraping ke database
            garuda_data(scraped_data, db)  

            results.extend(scraped_data)

    return {"message": "Scraping selesai dan data telah disimpan ke database!"}


@router.get("/scrape/scholar")
async def scrape_scholar(db: Session = Depends(get_db)):
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

@router.get("/sync/garuda")
async def sync_garuda(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")  # Debugging

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")  # Debugging
            
            # 🔹 Pastikan memanggil `scrape_garuda_data()` dengan argumen yang benar
            scraped_data = garuda_sync(lecturer_name, profile_link)
            
            print(f"Scraped data untuk {lecturer_name}: {scraped_data}")
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")  # Debugging
            
            # Simpan hasil scraping ke database
            garuda_data(scraped_data, db)  

            results.extend(scraped_data)

    return {"message": "Sync Data selesai, Data Telah Diperbarui!"}

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

@router.get("/sync/scholar")
async def sync_scholar(db: Session = Depends(get_db)):
    results = []

    # Mengambil data dosen dari database
    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"Memproses dosen: {lecturer_name}")

            scraped_data = scholar_sync(lecturer_name, profile_link)
            print(f"Jumlah data yang di-scrape: {len(scraped_data)}")

            scholar_data(scraped_data, db)

            results.extend(scraped_data)

    return {"message": "Sync Data Article Google Scholar Selesai"}

@router.get("/scrape/scholar/debug")
async def scrape_scholar_debug(db: Session = Depends(get_db)):
    results = []

    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen ditemukan: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"\n📚 Memproses: {lecturer_name}")
            google_scholar_url = f"{profile_link}?view=google_scholar"
            response = requests.get(google_scholar_url)

            if response.status_code != 200:
                print(f"Gagal mengambil data dari {google_scholar_url}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('div', class_='ar-list-item mb-5')

            for item in articles:
                title_tag = item.find('div', class_='ar-title')
                link_tag = title_tag.find('a') if title_tag else None
                title = link_tag.text.strip() if link_tag else 'N/A'
                publication_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else 'N/A'

                authors = []
                author_order = "N/A"
                meta_divs = item.find_all('div', class_='ar-meta')

                for div in meta_divs:
                    author_tag = div.find('a', href='#!')
                    if author_tag and "Authors :" in author_tag.text:
                        author_text = author_tag.text.strip()
                        authors_part = author_text.split("Authors :")[-1]
                        authors = [a.strip() for a in authors_part.split(',') if a.strip() and "..." not in a]
                        
                        # Normalisasi nama dosen → ambil nama belakang (atau nama unik)
                        lecturer_keywords = lecturer_name.lower().split()
                        for idx, name in enumerate(authors):
                            if any(key in name.lower() for key in lecturer_keywords if len(key) > 2):
                                author_order = str(idx + 1)
                                break
                        break  # selesai kalau sudah nemu authors

                results.append({
                    "lecturer_name": lecturer_name,
                    "title": title,
                    "publication_link": publication_link,
                    "authors": authors,
                    "author_order": author_order
                })

    return {"scraped_results": results}

@router.get("/scrape/garuda/debug")
async def scrape_garuda_debug(db: Session = Depends(get_db)):
    results = []

    lecturers = db.query(User.name, Author.sinta_profile_url).select_from(User).join(Author).all()
    print(f"Jumlah dosen ditemukan: {len(lecturers)}")

    for lecturer_name, profile_link in lecturers:
        if profile_link:
            print(f"\n📚 Memproses (GARUDA): {lecturer_name}")
            garuda_url = f"{profile_link}?view=garuda"
            print(f"🔗 Fetching from: {garuda_url}")
            response = requests.get(garuda_url)

            if response.status_code != 200:
                print(f"❌ Gagal mengambil data dari {garuda_url}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('div', class_='ar-list-item mb-5')

            for item in articles:
                title_tag = item.find('div', class_='ar-title').find('a')
                title = title_tag.text.strip() if title_tag else 'N/A'
                publication_link = title_tag['href'] if title_tag and title_tag.has_attr('href') else 'N/A'
                
                journal_category_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
                journal_category = journal_category_tag.text.strip() if journal_category_tag else 'N/A'

                second_meta_div = item.find_all('div', class_='ar-meta')[1] if len(item.find_all('div', class_='ar-meta')) > 1 else None
                author_order, year, doi, accred = 'N/A', 'N/A', 'N/A', 'N/A'
                authors = []

                if second_meta_div:
                    for a_tag in second_meta_div.find_all('a', href='#!'):
                        text = a_tag.text.strip()
                        if 'Author Order' in text:
                            match = re.search(r'\d+', text)
                            if match:
                                author_order = match.group()
                        else:
                            i_tag = a_tag.find('i')
                            if i_tag:
                                icon_class = i_tag.get('class', [])
                                if 'zmdi-calendar' in icon_class:
                                    year = text.replace('📅', '').strip()
                                elif 'zmdi-comment-list' in icon_class:
                                    doi = text.replace('🔗', '').replace('DOI: ', '').strip()
                                elif 'zmdi-chart-donut' in icon_class:
                                    accred = text.replace('📊', '').replace('Accred : ', '').strip()
                            else:
                                authors.append(text)

                results.append({
                    "lecturer_name": lecturer_name,
                    "title": title,
                    "publication_link": publication_link,
                    "journal_category": journal_category,
                    "authors": authors,
                    "author_order": author_order,
                    "year": year,
                    "doi": doi,
                    "accred": accred
                })

    return {"scraped_results": results}

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

@router.get("/scrape/abstract/garuda")
async def scrape_and_save_garuda_abstract(db: Session = Depends(get_db)):
    results = []

    articles = db.query(Article.id, Article.title, Article.article_url).filter(
        Article.source == "GARUDA",
        Article.abstract == None
    ).all()

    print(f"🔍 Jumlah artikel GARUDA tanpa abstract: {len(articles)}")

    scraped_data: List[GarudaAbstractResponse] = garuda_abstract_scraping(articles)

    print(f"💾 Mulai menyimpan {len(scraped_data)} abstract ke database...")

    for data in scraped_data:
        try:
            article = db.query(Article).filter_by(id=data.article_id).first()
            if article:
                article.abstract = data.abstract
                db.add(article)
                db.commit()
                results.append({
                    "id": article.id,
                    "title": article.title,
                    "abstract": article.abstract
                })
        except SQLAlchemyError as e:
            db.rollback()
            print(f"❌ Gagal simpan ID {data.article_id}: {str(e)}")

    return {
        "message": "Scraping GARUDA selesai dan abstract disimpan ke database!",
        "total_saved": len(results),
        "saved_data": results
    }

@router.get("/scrape/abstract/garuda/debug")
async def scrape_abstract_garuda_debug(db: Session = Depends(get_db)):
    # Ambil hanya artikel dari GARUDA yang abstract-nya masih kosong
    articles = db.query(Article).filter(
        Article.source == "GARUDA",
        Article.abstract == None
    ).all()

    print(f"📄 Total artikel GARUDA tanpa abstract: {len(articles)}")

    results = []

    for idx, article in enumerate(articles, start=1):
        title = article.title
        url = article.article_url
        abstract_text = "N/A"

        print(f"\n[{idx}/{len(articles)}] 🔍 Memproses: {title}")
        print(f"🌐 URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            abstract_div = soup.find("div", class_="abstract-article")

            if abstract_div:
                abstract_xmp = abstract_div.find("xmp", class_="abstract-article")
                abstract_text = abstract_xmp.text.strip() if abstract_xmp else "N/A"
                print(f"✅ Abstract ditemukan: {abstract_text[:50]}...")
            else:
                print("⚠️ Tidak menemukan div.abstract-article")

        except Exception as e:
            abstract_text = f"❌ Error: {str(e)}"
            print(f"❌ Gagal scraping: {str(e)}")

        results.append({
            "title": title,
            "article_url": url,
            "abstract": abstract_text
        })

        time.sleep(1)  # Biar nggak diblokir

    return {"scraped_abstracts": results}

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
                    "Status Penelitian": status_penelitian,
                    "Sumber Pendanaan": sumber_pendanaan
                }

                results.append(result_item)

            except Exception as e:
                print(f"⚠️ Gagal memproses 1 item: {e}")
                continue

        time.sleep(1)  # delay biar nggak dibanned

    return {"scraped_researches": results}


