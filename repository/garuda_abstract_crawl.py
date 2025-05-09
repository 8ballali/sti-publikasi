import requests
from fastapi import HTTPException
from bs4 import BeautifulSoup
import re, time
from typing import List
from schemas import PaperResponse, GarudaAbstractResponse
from sqlalchemy.orm import Session
from models import Article, User, Author, PublicationAuthor
import random
from sqlalchemy.exc import IntegrityError


def garuda_scrapping(lecturer_name: str, profile_link: str):
    garuda_url = f"{profile_link}?view=garuda"
    print(f'📡 Fetching data from: {garuda_url}')

    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Mozilla/5.0 (X11; Linux x86_64)',
        ]),
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        response = requests.get(garuda_url, headers=headers, timeout=10)
        time.sleep(3)  # Delay acak
    except Exception as e:
        log_error(f"[RequestError] {lecturer_name} - {garuda_url} - {str(e)}")
        return []

    papers = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.find_all('div', class_='ar-list-item mb-5')

        if not items:
            log_error(f"[NoData] {lecturer_name} - {garuda_url} - Halaman tidak mengandung publikasi.")
            return []

        for item in items:
            try:
                title_container = item.find('div', class_='ar-title')
                title_tag = title_container.find('a') if title_container else None
                title = title_tag.text.strip() if title_tag else 'N/A'
                publication_link = title_tag['href'] if title_tag and title_tag.has_attr('href') else 'N/A'

                meta_divs = item.find_all('div', class_='ar-meta')
                journal_category_tag = meta_divs[0].find('a', class_='ar-pub') if len(meta_divs) > 0 else None
                journal_category = journal_category_tag.text.strip() if journal_category_tag else 'N/A'

                second_meta_div = meta_divs[1] if len(meta_divs) > 1 else None
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

                papers.append(PaperResponse(
                    lecturer_name=lecturer_name,
                    title=title,
                    publication_link=publication_link,
                    journal_category=journal_category,
                    author_order=author_order,
                    authors=authors,
                    year=year,
                    doi=doi,
                    accred=accred
                ))
            except Exception as parse_error:
                log_error(f"[ParseError] {lecturer_name} - {garuda_url} - {parse_error}")
    else:
        log_error(f"[HTTPError] {lecturer_name} - {garuda_url} - Status code: {response.status_code}")
        print("Preview response content:", response.text[:300])

    return papers

def log_error(message: str):
    print("🚫", message)
    with open("garuda_scrape_errors.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")

def garuda_data(scraped_data: list[PaperResponse], db: Session):
    for data in scraped_data:
        # Cek apakah artikel sudah ada berdasarkan DOI atau judul
        article = db.query(Article).filter(
            (Article.doi == data.doi) | (Article.title == data.title)
        ).first()

        if not article:
            article = Article(
                title=data.title,
                year=int(data.year) if data.year.isdigit() else None,
                doi=data.doi if data.doi and data.doi.lower() != "none" else None,
                accred=data.accred,
                article_url=data.publication_link,
                journal=data.journal_category,
                source="GARUDA"
            )
            db.add(article)
            db.commit()
            db.refresh(article)

        # Proses semua penulis
        for idx, author_name in enumerate(data.authors):
            author = db.query(User).filter(User.name.ilike(f"%{author_name}%")).first()
            if not author:
                continue  # Lewati jika tidak ditemukan

            # Cek duplikat kombinasi article + author
            existing_relation = db.query(PublicationAuthor).filter_by(
                article_id=article.id,
                author_id=author.id
            ).first()

            if not existing_relation:
                author_order = int(data.author_order) if data.author_order and data.author_order.isdigit() else None
                db.add(PublicationAuthor(
                    article_id=article.id,
                    author_id=author.id,
                    author_order=author_order
                ))

    db.commit()




def garuda_sync(lecturer_name: str, profile_link: str):
    garuda_url = f"{profile_link}?view=garuda"
    print(f'Fetching data from: {garuda_url}')
    response = requests.get(garuda_url)

    papers = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.find_all('div', class_='ar-list-item mb-5')

        # Ambil hanya 5 artikel teratas
        items = items[:5]  # Hanya ambil 5 artikel pertama

        for item in items:
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

            papers.append(PaperResponse(
                lecturer_name=lecturer_name,
                title=title,
                publication_link=publication_link,
                journal_category=journal_category,
                author_order=author_order,
                authors=authors,
                year=year,
                doi=doi,
                accred=accred
            ))

    return papers

def garuda_abstract_scraping(article_list: List[tuple]) -> List[GarudaAbstractResponse]:
    results = []

    for idx, (article_id, title, url) in enumerate(article_list, start=1):
        print(f"\n[{idx}] 🔍 Scraping: {title}")
        print(f"🌐 URL: {url}")

        abstract_text = "N/A"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            abstract_div = soup.find("div", class_="abstract-article")

            if abstract_div:
                xmp = abstract_div.find("xmp", class_="abstract-article")
                abstract_text = xmp.text.strip() if xmp else "N/A"
                print("✅ Abstract ditemukan")
            else:
                print("⚠️ Abstract tidak ditemukan")

        except Exception as e:
            print(f"❌ Gagal scraping: {str(e)}")
            continue

        results.append(GarudaAbstractResponse(
            article_id=article_id,
            title=title,
            article_url=url,
            abstract=abstract_text
        ))

        time.sleep(1)  # untuk hindari rate-limit

    return results


def get_lecturers_with_profiles(db: Session):
    return db.query(User.name, Author.sinta_profile_url)\
             .select_from(User).join(Author).all()


def save_scraped_data_to_db(scraped_data: list[PaperResponse], db: Session):
    for paper in scraped_data:
        # 1. Cari atau buat article
        article = db.query(Article).filter(
            (Article.doi == paper.doi) | (Article.title == paper.title)
        ).first()

        if not article:
            article = Article(
                title=paper.title,
                year=int(paper.year) if paper.year and paper.year.isdigit() else None,
                doi=paper.doi if paper.doi and paper.doi.lower() != "none" else None,
                accred=paper.accred,
                article_url=paper.publication_link,
                journal=paper.journal_category,
                source="GARUDA"
            )
            db.add(article)
            db.commit()
            db.refresh(article)

        # 2. Cari author berdasarkan nama (user.name)
        user = db.query(User).filter(User.name.ilike(f"%{paper.lecturer_name}%")).first()
        if not user:
            continue  # lewati kalau author tidak ditemukan

        author = db.query(Author).filter_by(user_id=user.id).first()
        if not author:
            continue  # lewati kalau tidak ada relasi ke Author

        # 3. Tambahkan relasi article-author dengan pengecekan error duplikat
        author_order = int(paper.author_order) if paper.author_order and paper.author_order.isdigit() else None
        relation = PublicationAuthor(
            article_id=article.id,
            author_id=author.id,
            author_order=author_order
        )

        try:
            db.add(relation)
            db.flush()  # coba simpan ke memory, akan error jika duplikat
        except IntegrityError:
            db.rollback()  # batalkan relasi duplikat
            continue

    db.commit()
