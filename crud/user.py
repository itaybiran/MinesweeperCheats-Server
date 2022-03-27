import hashlib
from typing import List

from sqlalchemy.orm import Session

from utils.auth import hash_password
from utils.calculations import *
from models import user as user_models
from schemas import user as user_schemas
from utils.calculations import calculate_rank


def get_user(db: Session, user_id: int) -> user_models.User:
    return db.query(user_models.User).filter(user_models.User.id == user_id).first()


def get_user_by_nickname(db: Session, nickname: str) -> user_models.User:
    return db.query(user_models.User).filter(user_models.User.nickname == nickname).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[user_models.User]:
    return db.query(user_models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: user_schemas.UserCreate):
    hashed_password = hash_password(user.password)
    db_user = user_models.User(nickname=user.nickname, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_rank(db: Session, user: user_schemas.User, rank: int):
    user_to_update = get_user_by_nickname(db, user.nickname)
    user_to_update.rank = rank
    db.commit()
    return user_to_update


def update_user_xp(db: Session, user: user_schemas.User, xp: int):
    user_to_update = get_user_by_nickname(db, user.nickname)
    user_to_update.xp = xp
    db.commit()
    update_user_rank(db, user, calculate_rank(xp))
    return user_to_update
