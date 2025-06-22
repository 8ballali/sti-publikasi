from fastapi import FastAPI, Depends
from database import engine
import models
import os
from routes import authors,garuda,scopus, database, researches,stats
from routes.search import articles as search_articles, authors as search_authors, researches as search_researches
from routes.statistics import articles as stats_articles,researches as stats_researches, overall as stats_overall


from sqlalchemy.orm import Session
# Buat instance FastAPI
app = FastAPI()

# Buat tabel di database jika belum ada
models.Base.metadata.create_all(bind=engine)

print("✅ Loaded DB HOST:", os.getenv("DB_HOST"))



app = FastAPI(title="Publikasi API", version="1.0")

# Tambahkan router untuk endpoint scraping
app.include_router(authors.router, prefix="/api")
app.include_router(scopus.router, prefix="/api")
app.include_router(garuda.router, prefix="/api")
app.include_router(researches.router, prefix="/api")
app.include_router(search_articles.router, prefix="/api")
app.include_router(search_authors.router, prefix="/api")
app.include_router(search_researches.router, prefix="/api")
app.include_router(stats_overall.router, prefix="/api")
app.include_router(stats_articles.router, prefix="/api")
app.include_router(stats_researches.router, prefix="/api")
app.include_router(database.router, prefix="/api")
# app.include_router(stats.router, prefix="/api")



