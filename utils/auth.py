import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from constants import TOKEN_TTL, KEY, ALGORITHM
from models import user as user_models
from schemas import user as user_schemas


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request = None, websocket: WebSocket = None):
        if request:
            return await super().__call__(request)
        else:
            return await self.ws_call(websocket)

    async def ws_call(self, websocket: WebSocket) -> Optional[str]:
        authorization: str = websocket.headers.get("Authorization")
        scheme, param = self.get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            return None
        return param

    def get_authorization_scheme_param(self, authorization_header_value: str) -> Tuple[str, str]:
        if not authorization_header_value:
            return "", ""
        scheme, _, param = authorization_header_value.partition(" ")
        return scheme, param


oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl="users/token")


def decode_token(token):
    try:
        token_decrypt = jwt.decode(token, KEY, algorithms=[ALGORITHM])
        return user_schemas.User(
            nickname=token_decrypt["nickname"], rank=int(token_decrypt["rank"]), xp=int(token_decrypt["xp"])
        )
    except:
        return None


async def get_current_user_http(token: str = Depends(oauth2_scheme)):
    if token is not None:
        user = decode_token(token)
        return user
    else:
        raise HTTPException(400, "you are not authorized")


async def get_current_user_ws(token: str = Depends(oauth2_scheme)):
    if token is not None:
        user = decode_token(token)
        return user
    else:
        return None


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def generate_token(user: user_models.User):
    token = get_token_dict(user).copy()
    token.update({"exp": datetime.utcnow() + timedelta(minutes=TOKEN_TTL)})
    return jwt.encode(token, KEY, algorithm=ALGORITHM)


def get_token_dict(user: user_models.User) -> user_schemas.User:
    return {"nickname": user.nickname, "rank": user.rank, "xp": user.xp}
