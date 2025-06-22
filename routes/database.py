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
