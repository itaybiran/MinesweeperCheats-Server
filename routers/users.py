import json
from typing import List

from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from constants import ADMIN
from utils.auth import hash_password, generate_token, get_current_user_http, decode_token
from database import SessionLocal
from crud import user as user_crud
from schemas import user as user_schemas
from schemas import response as response_schemas
from schemas import token as token_schemas


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(
    prefix="/users"
)

logged_in_users = []


@router.get("/", response_model=List[user_schemas.User])
async def get_all(db: Session = Depends(get_db), user: user_schemas.User = Depends(get_current_user_http)):
    if user.nickname == ADMIN:
        users = user_crud.get_users(db)
        return users
    else:
        raise HTTPException(400, "you are not authorized")


@router.post("/register", response_model=response_schemas.Response)
async def register(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    """create a new account if nickname was not taken"""
    if user_crud.get_user_by_nickname(db, user.nickname):
        raise HTTPException(401, "nickname is already taken")
    else:
        user_crud.create_user(db, user)
        return {"response": "added user"}


@router.post("/token", response_model=token_schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """login to an existing account"""
    valid_user = user_crud.get_user_by_nickname(db, form_data.username)
    hashed_password = hash_password(form_data.password)
    if valid_user and valid_user.hashed_password == hashed_password:
        for logged_in_user in logged_in_users:
            if logged_in_user["user"].nickname == valid_user.nickname:
                if decode_token(logged_in_user["token"]["access_token"]) is not None:
                    raise HTTPException(401, "user is already connected")
                else:
                    logged_in_users.remove(logged_in_user)
        logged_in_users.append({"user": valid_user, "token": {"access_token": generate_token(valid_user), "token_type": "Bearer"}})
        return {"access_token": generate_token(valid_user), "token_type": "Bearer"}
    else:
        raise HTTPException(401, "wrong nickname or password")


@router.post("/save")
async def save_in_db(user_info: user_schemas.User, db: Session = Depends(get_db), user: user_schemas.User = Depends(get_current_user_http)):
    user.rank = user_info.rank
    user.xp = user_info.xp
    user_crud.update_user_info(db, user)
    return {"response": "saved data successfully"}


@router.get("/info", response_model=user_schemas.User)
async def get_user_info(db: Session = Depends(get_db), user: user_schemas.User = Depends(get_current_user_http)):
    if user:
        return user_crud.get_user_by_nickname(db, user.nickname)
    else:
        raise HTTPException(401, "you are not authorized")
