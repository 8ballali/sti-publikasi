import requests
from fastapi import HTTPException
from bs4 import BeautifulSoup
import re
from typing import List
from schemas import PaperResponse, PaperResponseScopus
from sqlalchemy.orm import Session
from models import Article, User, Author, PublicationAuthor


def scopus_scrapping(lecturer_name: str, profile_link: str) -> List[PaperResponseScopus]:
    results = []

    if not profile_link:
        return results

    scopus_url = f"{profile_link}?view=scopus"
    print(f"\n📚 Memproses (SCOPUS): {lecturer_name}")
    print(f"🔗 Fetching from: {scopus_url}")

    response = requests.get(scopus_url)
    if response.status_code != 200:
        print(f"❌ Gagal mengambil data dari {scopus_url}")
        return results

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('div', class_='ar-list-item mb-5')

    for item in articles:
        title_tag = item.find('div', class_='ar-title').find('a')
        title = title_tag.text.strip() if title_tag else 'N/A'

        accred_tag = item.find('div', class_='ar-meta').find('a', href='#!')
        accred = accred_tag.text.strip() if accred_tag else 'N/A'

        jurnal_tag = item.find('div', class_='ar-meta').find('a', class_='ar-pub')
        jurnal = jurnal_tag.text.strip() if jurnal_tag else 'N/A'

        first_meta_div = item.find('div', class_='ar-meta')
        
        # Perbaikan: pakai text= untuk konsistensi
        author_order_tag = first_meta_div.find('a', href="#!", text=lambda t: t and "Author Order" in t)
        author_order_text = author_order_tag.text.replace('Author Order : ', '').strip() if author_order_tag else None
        author_order = None
        if author_order_text:
            match = re.search(r'\d+', author_order_text)
            author_order = int(match.group()) if match else None

        creator_tag = first_meta_div.find('a', href="#!", text=lambda t: t and "Creator" in t)
        creator = creator_tag.text.replace('Creator : ', '').strip() if creator_tag else 'N/A'

        all_meta_divs = item.find_all('div', class_='ar-meta')
        year = None
        cited = 0
        if len(all_meta_divs) > 1:
            second_meta_div = all_meta_divs[1]

            year_tag = second_meta_div.find('a', class_='ar-year')
            year_text = year_tag.text.strip() if year_tag else None
            year = int(year_text) if year_text and year_text.isdigit() else None

            cited_tag = second_meta_div.find('a', class_='ar-cited')
            if cited_tag:
                cited_text = cited_tag.text.strip()
                match = re.search(r'\d+', cited_text)
                cited = int(match.group()) if match else None

        results.append(PaperResponseScopus(
            lecturer_name=lecturer_name,
            title=title,
            accred=accred,
            jurnal=jurnal,
            author_order=author_order,
            creator=creator,
            year=year,
            cited=cited,
        ))

    return results

def scopus_data(scraped_data: List[PaperResponseScopus], db: Session):
    for data in scraped_data:
        # Cek apakah artikel sudah ada
        article = db.query(Article).filter(
            Article.title == data.title
        ).first()

        if not article:
            article = Article(
                title=data.title,
                year=data.year,
                accred=data.accred,
                citation_count=data.cited,
                article_url=None,
                journal=data.jurnal,
                source="SCOPUS"
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

def scopus_sync(lecturer_name: str, profile_link: str):
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
