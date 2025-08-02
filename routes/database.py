from fastapi import APIRouter, Depends
from database import get_db
from fastapi import Depends, HTTPException
from database import Base, engine

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
