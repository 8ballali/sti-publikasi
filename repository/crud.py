# crud.py
from sqlalchemy.orm import Session
from sqlalchemy import or_ # Digunakan jika Anda ingin query dengan kondisi OR
from models import Research, Author, ResearcherAuthor # Pastikan mengimpor semua model yang relevan
from typing import List, Optional

def get_author_by_sinta_id(db: Session, sinta_id: str):
    """
    Mengambil objek Author dari database berdasarkan sinta_id.
    """
    return db.query(Author).filter(Author.sinta_id == sinta_id).first()

def create_author(db: Session, sinta_id: str, sinta_profile_url: Optional[str] = None):
    """
    Membuat entri Author baru di database.
    """
    db_author = Author(sinta_id=sinta_id, sinta_profile_url=sinta_profile_url)
    db.add(db_author)
    db.commit() # Commit perubahan ke database
    db.refresh(db_author) # Refresh objek untuk mendapatkan ID yang dihasilkan database
    return db_author

def get_research_by_title(db: Session, title: str):
    """
    Mengambil objek Research dari database berdasarkan judul.
    """
    return db.query(Research).filter(Research.title == title).first()

def create_research(db: Session, research_data: dict):
    """
    Membuat entri Research baru di database.
    Menerima dictionary research_data yang berisi data penelitian.
    """
    db_research = Research(
        title=research_data["title"],
        fund=research_data.get("dana"), # Gunakan .get() agar tidak error jika key tidak ada
        fund_status=research_data.get("status"),
        fund_source=research_data.get("sumber"),
        fund_type=research_data.get("jenis_penelitian"),
        year=research_data.get("year")
    )
    db.add(db_research)
    # db.commit() # Commit dilakukan di main.py setelah memproses satu item lengkap
    # db.refresh(db_research) # Refresh dilakukan di main.py
    return db_research

def get_researcher_author(db: Session, research_id: int, author_id: int):
    """
    Mengambil objek ResearcherAuthor dari database berdasarkan research_id dan author_id.
    Digunakan untuk mengecek apakah relasi penelitian-penulis sudah ada.
    """
    return db.query(ResearcherAuthor).filter(
        ResearcherAuthor.researcher_id == research_id,
        ResearcherAuthor.author_id == author_id
    ).first()

def add_researcher_to_research(db: Session, research_id: int, author_id: int, is_leader: bool):
    """
    Menambahkan relasi antara penelitian dan penulis di tabel ResearcherAuthor.
    """
    db_researcher_author = ResearcherAuthor(
        researcher_id=research_id,
        author_id=author_id,
        is_leader=is_leader
    )
    db.add(db_researcher_author)
    # db.commit() # Commit dilakukan di main.py setelah memproses satu item lengkap
    # db.refresh(db_researcher_author) # Refresh dilakukan di main.py
    return db_researcher_author

def get_all_authors(db: Session) -> List[Author]:
    """
    Mengambil semua objek Author dari database.
    """
    return db.query(Author).all()


