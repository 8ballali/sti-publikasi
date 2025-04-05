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
