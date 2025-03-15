from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables dari .env
# load_dotenv()

# # Ambil URL database dari .env
# SQLALCHEMY_DATABASE_URL = os.getenv("SQL_URL")

# # Pastikan tidak None dan gunakan driver MySQL dengan pymysql
# if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
#     SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://")

# # Pastikan SQLALCHEMY_DATABASE_URL tidak kosong
# if not SQLALCHEMY_DATABASE_URL:
#     raise ValueError("Database URL tidak ditemukan. Pastikan SQL_URL sudah ada di .env")

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@localhost/sti_publikasi"

engine = create_engine(SQLALCHEMY_DATABASE_URL)


# Buat session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Buat deklarasi model
Base = declarative_base()

# Dependency untuk mendapatkan session database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
