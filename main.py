from fastapi import FastAPI, Depends
from database import engine
import models
from routes import crawl

from sqlalchemy.orm import Session
# Buat instance FastAPI
app = FastAPI()

# Buat tabel di database jika belum ada
models.Base.metadata.create_all(bind=engine)


app = FastAPI()

# Tambahkan router untuk endpoint scraping
app.include_router(crawl.router, prefix="/api")



# @app.get("/scrape")
# async def scrape_sinta():
#     results = []

#     for page in range(1, 3):
#         url = f"{BASE_URL}?page={page}"
#         response = requests.get(url, headers=HEADERS)

#         if response.status_code == 200:
#             soup = BeautifulSoup(response.content, "html.parser")
#             author_sections = soup.find_all("div", class_="au-item mt-3 mb-3 pb-5 pt-3")

#             for author in author_sections:
#                 name_tag = author.find("a")
#                 name = name_tag.get_text(strip=True) if name_tag else "N/A"
#                 profile_link = "" + name_tag["href"] if name_tag else "N/A"

#                 sinta_id_tag = author.find("div", class_="profile-id")
#                 sinta_id = sinta_id_tag.get_text(strip=True).replace("ID : ", "") if sinta_id_tag else "N/A"

#                 score_blocks = author.find_all("div", class_="stat-num text-center")
#                 sinta_score_3yr = score_blocks[0].get_text(strip=True) if len(score_blocks) >= 2 else "N/A"
#                 sinta_score_total = score_blocks[1].get_text(strip=True) if len(score_blocks) >= 2 else "N/A"
#                 affil_score_3yr = score_blocks[2].get_text(strip=True) if len(score_blocks) >= 4 else "N/A"
#                 affil_score_total = score_blocks[3].get_text(strip=True) if len(score_blocks) >= 4 else "N/A"

#                 results.append(
#                     CrawlAuthors(
#                         lecturer_name=name,
#                         sinta_id=sinta_id,
#                         profile_link=profile_link,
#                         sinta_score_3yr=sinta_score_3yr,
#                         sinta_score_total=sinta_score_total,
#                         affil_score_3yr=affil_score_3yr,
#                         affil_score_total=affil_score_total
#                     )
#                 )
#                 time.sleep(1)
#                 print(f"✅ {name} | ID: {sinta_id} | Score 3yr: {sinta_score_3yr} | Total: {sinta_score_total} | Affil 3yr: {affil_score_3yr} | Affil Total: {affil_score_total}")
#         else:
#             return {"error": f"Gagal mengakses halaman {page}, status {response.status_code}"}

#     return {"data": results}