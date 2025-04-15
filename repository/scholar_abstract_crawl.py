import requests
from bs4 import BeautifulSoup
import re
from models import Article, User, PublicationAuthor  # pastikan ini sesuai dengan project-mu
from schemas import PaperResponseScholar  # asumsi ini sama seperti yang digunakan di Garuda
from sqlalchemy.orm import Session

from typing import List
from bs4 import BeautifulSoup
import requests

def scholar_scrapping(lecturer_name: str, profile_link: str) -> List[PaperResponseScholar]:
    google_scholar_url = f"{profile_link}?view=google_scholar"
    print(f'Fetching data from: {google_scholar_url}')
    response = requests.get(google_scholar_url)

    papers = []

    if response.status_code != 200:
        print(f"Gagal mengambil data dari {google_scholar_url}")
        return papers

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('div', class_='ar-list-item mb-5')

    for item in articles:
        # Title dan Link
        title_tag = item.find('div', class_='ar-title')
        link_tag = title_tag.find('a') if title_tag else None
        title = link_tag.text.strip() if link_tag else 'N/A'
        publication_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else 'N/A'

        authors = []
        author_order = None
        meta_divs = item.find_all('div', class_='ar-meta')

        for div in meta_divs:
            author_tag = div.find('a', href='#!')
            if author_tag and "Authors :" in author_tag.text:
                author_text = author_tag.text.strip()
                authors_part = author_text.split("Authors :")[-1]
                authors = [a.strip() for a in authors_part.split(',') if a.strip() and "..." not in a]

                # Normalisasi nama dosen → pecah jadi keyword (e.g. ['ajib', 'susanto'])
                lecturer_keywords = lecturer_name.lower().split()

                for idx, name in enumerate(authors):
                    if any(key in name.lower() for key in lecturer_keywords if len(key) > 2):
                        author_order = idx + 1
                        break
                break  # keluar kalau sudah nemu authors

        # Journal
        journal_category_tag = item.find('a', class_='ar-pub')
        journal_category = journal_category_tag.text.strip() if journal_category_tag else 'N/A'

        # Tahun dan Cited
        year = None
        cited = None
        if len(meta_divs) > 1:
            for a_tag in meta_divs[1].find_all('a', href='#!'):
                text = a_tag.text.strip()
                i_tag = a_tag.find('i')
                if i_tag:
                    icon_class = i_tag.get('class', [])
                    if 'zmdi-calendar' in icon_class:
                        year = text.replace('📅', '').strip()
                    elif 'zmdi-comment-list' in icon_class:
                        cited = text.replace('🔗', '').strip()

        papers.append(PaperResponseScholar(
            lecturer_name=lecturer_name,
            title=title,
            publication_link=publication_link,
            journal_category=journal_category,
            author_order=author_order,
            authors=authors,
            year=year,
            cited=cited
        ))

    return papers




def scholar_data(scraped_data: list[PaperResponseScholar], db: Session):
    for data in scraped_data:
        # Cek apakah artikel sudah ada
        article = db.query(Article).filter(
            (Article.title == data.title)
        ).first()

        if not article:
            article = Article(
                title=data.title,
                year=int(data.year) if data.year.isdigit() else None,
                article_url=data.publication_link,
                journal=data.journal_category,
                source="GOOGLE_SCHOLAR"
            )
            db.add(article)
            db.commit()
            db.refresh(article)

        # Cek apakah dosen sudah ada
        author = db.query(User).filter(User.name.ilike(f"%{data.lecturer_name}%")).first()
        if author:
            author_id = author.id
            existing_relation = db.query(PublicationAuthor).filter_by(
                article_id=article.id,
                author_id=author_id,
            ).first()

            if not existing_relation:
                new_relation = PublicationAuthor(
                    article_id=article.id,
                    author_id=author_id,
                    author_order=data.author_order
                )
                db.add(new_relation)
    db.commit()
