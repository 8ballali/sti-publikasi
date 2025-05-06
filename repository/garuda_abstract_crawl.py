import requests
from fastapi import HTTPException
from bs4 import BeautifulSoup
import re, time
from typing import List
from schemas import PaperResponse, GarudaAbstractResponse
from sqlalchemy.orm import Session
from models import Article, User, Author, PublicationAuthor
import random


def garuda_scrapping(lecturer_name: str, profile_link: str):
    garuda_url = f"{profile_link}?view=garuda"
    print(f'Fetching data from: {garuda_url}')

    # Tambahkan headers agar tidak terdeteksi sebagai bot
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Mozilla/5.0 (X11; Linux x86_64)',
        ]),
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        response = requests.get(garuda_url, headers=headers)
        time.sleep(1)  # jeda sejenak agar tidak dianggap bot
    except Exception as e:
        print(f"Request error: {e}")
        return []

    papers = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        for item in soup.find_all('div', class_='ar-list-item mb-5'):
            title_tag = item.find('div', class_='ar-title').find('a')
            title = title_tag.text.strip() if title_tag else 'N/A'
            publication_link = title_tag['href'] if title_tag and title_tag.has_attr('href') else 'N/A'
            journal_category_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
            journal_category = journal_category_tag.text.strip() if journal_category_tag else 'N/A'

            second_meta_div = item.find_all('div', class_='ar-meta')[1] if len(item.find_all('div', 'ar-meta')) > 1 else None
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
    else:
        print(f"[{response.status_code}] Failed to fetch: {garuda_url}")
        print("Response content:")
        print(response.text[:1000])  # hanya tampilkan 1000 karakter pertama untuk debug

    return papers

def garuda_data(scraped_data: list[PaperResponse], db: Session):
    for data in scraped_data:
        # Cek apakah artikel sudah ada berdasarkan DOI atau judul
        article = db.query(Article).filter(
            (Article.doi == data.doi) | (Article.title == data.title)
        ).first()

        if not article:
            # Jika artikel belum ada, buat entri baru
            article = Article(
                title=data.title,
                year=int(data.year) if data.year.isdigit() else None,
                doi=data.doi if data.doi and data.doi.lower() != "none" else None,
                accred=data.accred,
                article_url=data.publication_link,
                journal=data.journal_category,
                source = "GARUDA"
            )
            db.add(article)
            db.commit()  # Commit setelah menambahkan artikel
            db.refresh(article)  # Refresh agar ID tersedia

        # Cek apakah author sudah ada di tabel User berdasarkan `lecturer_name`
        author = db.query(User).filter(User.name.ilike(f"%{data.lecturer_name}%")).first()

        if author:
            author_id = author.id

            # Cek apakah relasi author-article sudah ada di PublicationAuthor
            existing_relation = db.query(PublicationAuthor).filter_by(
                article_id=article.id,
                author_id=author_id,
            ).first()

            if not existing_relation:
                new_relation = PublicationAuthor(
                    article_id=article.id,
                    author_id=author_id,
                    author_order=int(data.author_order) if data.author_order.isdigit() else 0
                )
                db.add(new_relation)
    db.commit()  # Commit setelah menambahkan relasi author-article

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

