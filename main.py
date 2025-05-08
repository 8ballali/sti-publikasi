from fastapi import FastAPI, Depends
from database import engine
import models
from routes import authors,garuda,scholar,scopus, database, searching, researches

from sqlalchemy.orm import Session
# Buat instance FastAPI
app = FastAPI()

# Buat tabel di database jika belum ada
models.Base.metadata.create_all(bind=engine)


app = FastAPI()

# Tambahkan router untuk endpoint scraping
app.include_router(authors.router, prefix="/api")
app.include_router(garuda.router, prefix="/api")
app.include_router(scholar.router,prefix="/api")
app.include_router(scopus.router, prefix="/api")
app.include_router(researches.router, prefix="/api")
app.include_router(database.router, prefix="/api")
app.include_router(searching.router, prefix="/api")


