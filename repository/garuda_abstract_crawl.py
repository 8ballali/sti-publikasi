import requests
from bs4 import BeautifulSoup
import re
from typing import List
from schemas import PaperResponse
from sqlalchemy.orm import Session
from models import Article, User, Author, PublicationAuthor

def scrape_garuda_data(lecturer_name: str, profile_link: str) -> List[PaperResponse]:
    garuda_url = f"{profile_link}?view=garuda"
    print(f'Fetching data from: {garuda_url}')
    response = requests.get(garuda_url)

    papers = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        for item in soup.find_all('div', class_='ar-list-item mb-5'):
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

def save_scraped_data(db: Session, scraped_data: List[PaperResponse]):
    for paper in scraped_data:
        # Cek apakah artikel sudah ada di database berdasarkan DOI atau judul
        article = db.query(Article).filter((Article.doi == paper.doi) | (Article.title == paper.title)).first()

        if not article:
            # Jika artikel belum ada, simpan ke tabel articles
            article = Article(
                title=paper.title,
                year=int(paper.year) if paper.year.isdigit() else None,
                doi=paper.doi if paper.doi != "N/A" else None,
                accred=paper.accred,
                article_url=paper.publication_link,
                journal=paper.journal_category,
                abstract="",
                citation_count=None
            )
            db.add(article)
            db.commit()
            db.refresh(article)  # Mendapatkan ID yang baru saja disimpan
        
        # Cek apakah lecturer_name ada di tabel User
        lecturer = db.query(User).filter(User.name == paper.lecturer_name).first()

        if lecturer:
            lecturer_id = lecturer.id
        else:
            lecturer_id = None  # Jika tidak ditemukan, tidak bisa dimasukkan ke publication_authors

        # Simpan data author dan hubungan dengan artikel
        for author_name in paper.authors:
            author = db.query(Author).filter(Author.name == author_name).first()
            if not author:
                author = Author(name=author_name)
                db.add(author)
                db.commit()
                db.refresh(author)
            
            # Jika author cocok dengan lecturer_name, gunakan lecturer_id sebagai author_id
            if author.name == paper.lecturer_name and lecturer_id:
                author_id = lecturer_id
            else:
                author_id = author.id

            # Cek apakah sudah ada hubungan antara author dan article
            pub_author = db.query(PublicationAuthor).filter_by(article_id=article.id, author_id=author_id).first()
            if not pub_author:
                pub_author = PublicationAuthor(
                    article_id=article.id,
                    author_id=author_id,
                    author_order=int(paper.author_order) if paper.author_order.isdigit() else 0
                )
                db.add(pub_author)

        db.commit()