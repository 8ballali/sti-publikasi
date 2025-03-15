from sqlalchemy.orm import Session
from models import User, Author
from schemas import UserCreate, AuthorCreate

def create_user_and_author(user_data: UserCreate, author_data: AuthorCreate, db: Session):
    new_user = User(name=user_data.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_author = Author(
        user_id=new_user.id,
        sinta_score_3yr=author_data.sinta_score_3yr,
        sinta_score_total=author_data.sinta_score_total,
        affil_score_3yr=author_data.affil_score_3yr,
        affil_score_total=author_data.affil_score_total,
        subject=author_data.subject
    )

    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return {"user": new_user, "author": new_author}
