from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    author = relationship("Author", back_populates="user", uselist=False)

class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    sinta_profile_url = Column(String(255), nullable=True)
    sinta_id = Column(String(255), nullable=True)
    sinta_score_3yr = Column(String(255), nullable=True)
    sinta_score_total = Column(String(255), nullable=True)
    affil_score_3yr = Column(String(255), nullable=True)
    affil_score_total = Column(String(255), nullable=True)
    scopus_hindex = Column(String(255), nullable=True)
    gs_hindex = Column(String(255), nullable=True)
    department = Column(String(255))


    user = relationship("User", back_populates="author")
    publications = relationship("PublicationAuthor", back_populates="author")
    research = relationship("ResearcherAuthor", back_populates="author")
    subjects = relationship("UserSubject", back_populates="author")


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    year = Column(Integer)
    doi = Column(String(255), default="None", nullable=True)
    accred = Column(String(255), nullable=True)
    abstract = Column(Text)
    citation_count = Column(Integer, nullable=True)
    article_url = Column(Text, nullable=True)
    journal = Column(String(255))
    source = Column(String(255))
    university = Column(String(255))
    authors = relationship("PublicationAuthor", back_populates="article")
    keywords = relationship("ArticleKeyword", back_populates="article")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)

    authors = relationship("UserSubject", back_populates="subject")

class UserSubject(Base):
    __tablename__ = "user_subjects"
    id = Column(Integer, primary_key=True, index=True)

    author_id = Column(Integer, ForeignKey("authors.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))

    author = relationship("Author", back_populates="subjects")
    subject = relationship("Subject", back_populates="authors")


class Research(Base):
    __tablename__ = "research"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    fund = Column(Integer)
    fund_status = Column(String(255))
    fund_source = Column(String(255))
    fund_type = Column(String(255))
    year = Column(Integer)
    authors = relationship("ResearcherAuthor", back_populates="research")

class ResearcherAuthor(Base):
    __tablename__ = "researchers_authors"
    id = Column(Integer, primary_key=True, index=True)
    researcher_id = Column(Integer, ForeignKey("research.id"))
    author_id = Column(Integer, ForeignKey("authors.id"))
    is_leader = Column(Boolean, default=False)
    research = relationship("Research", back_populates="authors")
    author = relationship("Author", back_populates="research")

class PublicationAuthor(Base):
    __tablename__ = "publication_authors"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    author_id = Column(Integer, ForeignKey("authors.id"))
    author_order = Column(Integer, nullable=True)
    article = relationship("Article", back_populates="authors")
    author = relationship("Author", back_populates="publications")
    __table_args__ = (
    UniqueConstraint('article_id', 'author_id', name='uq_article_author'),
)


class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), unique=True, nullable=False)
    articles = relationship("ArticleKeyword", back_populates="keyword")

class ArticleKeyword(Base):
    __tablename__ = "article_keywords"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    keyword_id = Column(Integer, ForeignKey("keywords.id"))
    article = relationship("Article", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="articles")