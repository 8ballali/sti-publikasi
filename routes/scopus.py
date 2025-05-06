from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import User, Author, Article
from repository.scopus_abstract_crawl import scopus_scrapping,scopus_data, scopus_sync
import pandas as pd
from io import StringIO
from difflib import get_close_matches
import requests,time
import re, random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import unicodedata
from selenium.webdriver.support import expected_conditions as EC



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


def scrape_abstract_google_scholar(articles):
    # Set up Chrome with undetected_chromedriver
    options = Options()
    ua = UserAgent()
    options.add_argument(f"user-agent={ua.random}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless")

    # Start Chrome
    driver = uc.Chrome(options=options)
    driver.get("https://scholar.google.com")
    
    # Results to store
    scraped_data = []

    for article in articles:
        try:
            title = article.title
            print(f"🔍 Searching for: {title}")

            # Search the article title on Google Scholar
            search_box = driver.find_element(By.NAME, "q")
            search_box.clear()
            search_box.send_keys(title)
            search_box.send_keys(Keys.RETURN)
            time.sleep(random.randint(4,6))  # Sleep to mimic human behavior

            abstract = "Not Found"
            article_link = "Not Found"

            try:
                result_element = driver.find_element(By.CLASS_NAME, "gs_ri")

                # Ambil link artikel dari class gs_rt
                try:
                    article_element = result_element.find_element(By.CLASS_NAME, "gs_rt").find_element(By.TAG_NAME, "a")
                    article_link = article_element.get_attribute("href")
                except:
                    pass  

                # Cari abstrak di berbagai kemungkinan class
                try:
                    abstract_element = result_element.find_element(By.CLASS_NAME, "gs_fma_snp")
                    abstract = abstract_element.text.strip()
                except:
                    try:
                        abstract_element = result_element.find_element(By.CLASS_NAME, "gsh_csp")
                        abstract = abstract_element.text.strip()
                    except:
                        try:
                            abstract_element = result_element.find_element(By.CLASS_NAME, "gs_rs")
                            abstract = abstract_element.text.strip()
                        except:
                            pass  

            except Exception as e:
                print(f"Error retrieving data: {e}")

            # Append the data to scraped_data
            scraped_data.append({
                "article_id": article.id,
                "title": article.title,
                "abstract": abstract,
                "article_link": article_link
            })

        except Exception as e:
            print(f"Error scraping article {article.title}: {str(e)}")

    driver.quit()
    return scraped_data

@router.get("/scrape/abstract/google-scholar")
async def abstract_google_scholar(db: Session = Depends(get_db)):
    results = []

    # Ambil artikel yang belum memiliki abstrak dari database (hanya 10 artikel untuk testing)
    articles = db.query(Article.id, Article.title).filter(Article.abstract == None).limit(10).all()

    print(f"🔍 Jumlah artikel tanpa abstrak: {len(articles)}")

    if not articles:
        raise HTTPException(status_code=404, detail="No articles found to scrape")

    # Scraping abstract menggunakan fungsi scrape_abstract_google_scholar
    scraped_data = scrape_abstract_google_scholar(articles)

    print(f"💾 Menampilkan {len(scraped_data)} abstrak yang ditemukan:")

    # Kumpulkan hasil scraping tanpa menyimpan ke database
    for data in scraped_data:
        results.append({
            "id": data['article_id'],
            "title": data['title'],
            "abstract": data['abstract'],
            "article_link": data['article_link']
        })

    return {
        "message": "Scraping selesai!",
        "scraped_data": results
    }



def normalize(text: str) -> str:
    # Ubah ke huruf kecil
    text = text.lower()

    # Hilangkan accent/diakritik (contoh: é -> e)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')

    # Hilangkan karakter non-alfabet dan angka (kecuali spasi)
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # Hilangkan spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    return text

@router.post("/scopus/upload-abstracts")
async def upload_abstracts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        csv_buffer = StringIO(contents.decode('utf-8'))
        df = pd.read_csv(csv_buffer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

    if df.shape[1] < 9:
        raise HTTPException(status_code=400, detail="CSV file must have at least 9 columns.")

    updated_count = 0
    unmatched_titles = []

    # Ambil hanya artikel dari source SCOPUS
    all_articles = db.query(Article).filter(Article.source == "SCOPUS").all()
    normalized_db_titles = {normalize(article.title): article for article in all_articles}

    for index, row in df.iterrows():
        csv_title_raw = str(row.iloc[1]).strip()        # kolom ke-2: judul
        raw_article_url = row.iloc[7]
        new_article_url = str(raw_article_url).strip() if not pd.isna(raw_article_url) else ""
        raw_abstract = row.iloc[8]
        new_abstract = str(raw_abstract).strip() if not pd.isna(raw_abstract) else ""


        normalized_csv_title = normalize(csv_title_raw)
        match = get_close_matches(normalized_csv_title, normalized_db_titles.keys(), n=1, cutoff=0.8)

        if match:
            matched_article = normalized_db_titles[match[0]]
            matched_article.abstract = new_abstract

            if new_article_url:  # hanya update jika kolom 7 tidak kosong
                matched_article.article_url = new_article_url

            updated_count += 1
        else:
            unmatched_titles.append(csv_title_raw)

    db.commit()

    return {
        "message": f"{updated_count} articles updated successfully.",
        "unmatched_titles": unmatched_titles
    }

