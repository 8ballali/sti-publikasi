# services/sinta_scraper.py
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from models import User, Author, Research, ResearcherAuthor
import re

def research_sync(sinta_id: str):
    base_url = f"https://sinta.kemdikbud.go.id/authors/profile/{sinta_id}?view=researches"
    response = requests.get(base_url)
    
    results = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.find_all('div', class_='ar-list-item mb-5')[:5]

        for item in items:
            try:
                title_tag = item.find('div', class_='ar-title')
                title = title_tag.text.strip() if title_tag else 'N/A'

                meta_divs = item.find_all('div', class_='ar-meta')
                first_meta = meta_divs[0] if len(meta_divs) > 0 else None
                second_meta = meta_divs[1] if len(meta_divs) > 1 else None
                third_meta = meta_divs[2] if len(meta_divs) > 2 else None

                leader = 'N/A'
                fund_type = 'N/A'
                if first_meta:
                    for a_tag in first_meta.find_all('a'):
                        text = a_tag.text.strip()
                        if 'Leader :' in text:
                            leader = text.replace('Leader :', '').strip()
                        elif a_tag.get('class') == ['ar-pub']:
                            fund_type = text

                personils = []
                if second_meta:
                    personils = [a.text.strip() for a in second_meta.find_all('a') if a.text.strip() and "Personils" not in a.text]

                # Tahun, Dana, Status, Sumber
                year = fund = status = source = 'N/A'
                if third_meta:
                    for a in third_meta.find_all('a'):
                        text = a.text.strip()
                        class_attr = a.get('class', [])

                        if "ar-year" in class_attr:
                            year = text
                        elif "ar-quartile text-success" in " ".join(class_attr):
                            status = text
                        elif "ar-quartile text-info" in " ".join(class_attr):
                            source = text
                        elif "ar-quartile" in class_attr and not any("text" in cls for cls in class_attr):
                            fund = text.replace("Rp", "").replace(".", "").strip()


                results.append({
                    "title": title,
                    "leader": leader,
                    "fund_type": fund_type,
                    "personils": personils,
                    "year": year,
                    "fund": fund,
                    "fund_status": status,
                    "fund_source": source
                })
            except Exception as e:
                print(f"Error parsing item: {e}")
    return results