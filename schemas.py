from pydantic import BaseModel
from typing import Optional, List

class CrawlAuthors(BaseModel):
    lecturer_name: str
    sinta_profile_url: str
    sinta_id: str
    profile_link: str
    sinta_score_3yr: str
    sinta_score_total: str
    affil_score_3yr: str
    affil_score_total: str

class UserCreate(BaseModel):
    name: str

class AuthorCreate(BaseModel):
    user_id: int
    sinta_profile_url: str
    sinta_score_3yr: Optional[int] = None
    sinta_score_total: Optional[int] = None
    affil_score_3yr: Optional[int] = None
    affil_score_total: Optional[int] = None



class PaperResponse(BaseModel):
    lecturer_name: str
    title: str
    publication_link: str
    journal_category: str
    author_order: str
    authors: List[str]
    year: str
    doi: Optional[str] = None
    accred: Optional[str] = None

class PaperResponseScholar(BaseModel):
    lecturer_name: str
    title: str
    publication_link: str
    journal_category: str
    author_order: Optional[int]
    authors: List[str]
    year: str


    class Config:
        orm_mode = True