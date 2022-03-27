from datetime import datetime, timedelta
import hashlib

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from constants import TOKEN_TTL, KEY, ALGORITHM
from schemas import user as user_schemas
from models import user as user_models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")


def decode_token(token):
    token_decrypt = jwt.decode(token, KEY, algorithms=[ALGORITHM])
    return user_schemas.User(
        nickname=token_decrypt["nickname"], rank=int(token_decrypt["rank"]), xp=int(token_decrypt["xp"])
    )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    return user


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def generate_token(user: user_models.User):
    token = get_token_dict(user).copy()
    token.update({"exp": datetime.utcnow() + timedelta(minutes=TOKEN_TTL)})
    return jwt.encode(token, KEY, algorithm=ALGORITHM)


def get_token_dict(user: user_models.User) -> user_schemas.User:
    return {"nickname": user.nickname, "rank": user.rank, "xp": user.xp}
