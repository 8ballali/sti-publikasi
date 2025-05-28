from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os



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
