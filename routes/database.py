from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session
from database import Base, engine

router = APIRouter()

router = APIRouter(
    tags=['Database']
)


@router.post("/reset-all")
def reset_all():
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"message": "Database reset: structure and data cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-database")
def reset_database(db: Session = Depends(get_db)):
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        return {"message": "All data deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")