from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
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
    sinta_score_3yr = Column(Integer, nullable=True)
    sinta_score_total = Column(Integer, nullable=True)
    affil_score_3yr = Column(Integer, nullable=True)
    affil_score_total = Column(Integer, nullable=True)
    subject = Column(String(255), nullable=True)
    user = relationship("User", back_populates="author")
    publications = relationship("PublicationAuthor", back_populates="author")
    researches = relationship("ResearcherAuthor", back_populates="author")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    year = Column(Integer)
    doi = Column(String(255), default="None", nullable=True)
    accred = Column(String(255), nullable=True)
    abstract = Column(Text)
    citation_count = Column(Integer, nullable=True)
    article_url = Column(Text)
    journal = Column(String(255))
    source = Column(String(255))
    authors = relationship("PublicationAuthor", back_populates="article")
    keywords = relationship("ArticleKeyword", back_populates="article")

class Research(Base):
    __tablename__ = "researchers"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    fund = Column(Float)
    fund_source = Column(String(255))
    fund_status = Column(String(255))
    year = Column(Integer)
    authors = relationship("ResearcherAuthor", back_populates="research")

class ResearcherAuthor(Base):
    __tablename__ = "researchers_authors"
    id = Column(Integer, primary_key=True, index=True)
    researcher_id = Column(Integer, ForeignKey("researchers.id"))
    author_id = Column(Integer, ForeignKey("authors.id"))
    author_order = Column(Integer)
    research = relationship("Research", back_populates="authors")
    author = relationship("Author", back_populates="researches")

class PublicationAuthor(Base):
    __tablename__ = "publication_authors"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    author_id = Column(Integer, ForeignKey("authors.id"))
    author_order = Column(Integer, nullable=True)
    article = relationship("Article", back_populates="authors")
    author = relationship("Author", back_populates="publications")

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
