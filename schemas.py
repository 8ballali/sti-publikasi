from pydantic import BaseModel
from typing import Optional, List, Any


class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
class CrawlAuthors(BaseModel):
    lecturer_name: str
    sinta_profile_url: str
    sinta_id: str
    profile_link: str
    scopus_hindex: str
    gs_hindex: str
    sinta_score_3yr: str
    sinta_score_total: str
    affil_score_3yr: str
    affil_score_total: str
    department: str


class UserCreate(BaseModel):
    name: str

class AuthorCreate(BaseModel):
    user_id: int
    sinta_profile_url: str
    sinta_score_3yr: Optional[int] = None
    sinta_score_total: Optional[int] = None
    affil_score_3yr: Optional[int] = None
    affil_score_total: Optional[int] = None
    subject: List[str] = [] 



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

class PaperResponseScopus(BaseModel):
    lecturer_name: str
    title: str
    accred: Optional[str] = None
    jurnal: Optional[str] = None
    author_order: Optional[int] = None
    creator: Optional[str] = None
    year: Optional[int] = None
    cited: Optional[int] = 0

class GarudaAbstractResponse(BaseModel):
    article_id: int
    title: str
    article_url: str
    abstract: str

class ResearchResponse(BaseModel):
    title: str
    leader: str
    jenis_penelitian: str
    personils: Optional[str]
    year: Optional[int]
    dana_penelitian: int
    status_penelitian: str
    sumber_pendanaan: str
    author_name:str
    author_id: int

    class Config:
        orm_mode = True


class ArticleAuthorItem(BaseModel):
    name: str
    author_order: Optional[int]


class ArticleResponse(BaseModel):
    id: int
    title: str
    abstract: Optional[str] = None
    year: Optional[int]
    article_url: Optional[str]
    journal: Optional[str]
    doi: Optional[str] = None
    source: Optional[str]
    author_order: Optional[int]
    author_name: Optional[str] = None
    author_id: Optional[int] = None

    class Config:
        orm_mode = True

class ArticleWithAuthorsResponse(BaseModel):
    id: int
    title: str
    year: Optional[int]
    doi: Optional[str]
    accred: Optional[str] = None
    citation_count: Optional[int] = None
    article_url: Optional[str] = None
    journal: Optional[str] = None
    source: Optional[str] = None
    authors: List[ArticleAuthorItem]


class SubjectItem(BaseModel):
    name: Optional[str]

class AuthorSearchResponse(BaseModel):
    id: int
    name: str
    articles: List[ArticleResponse]
    researches: List[ResearchResponse]

    class Config:
        orm_mode = True

class AuthorDetailResponse(BaseModel):
    id: int
    name: Optional[str]  # from User
    sinta_profile_url: Optional[str]
    sinta_score_3yr: Optional[str]
    sinta_score_total: Optional[str]
    affil_score_3yr: Optional[str]
    affil_score_total: Optional[str]
    subjects: List[str]
    articles: List[ArticleResponse]
    researches: List[ResearchResponse]



class TopAuthorResponse(BaseModel):
    author_id: int
    name: str
    article_count: int