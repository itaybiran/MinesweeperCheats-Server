import datetime

from pydantic import BaseModel


class UserBase(BaseModel):
    nickname: str

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str


class User(UserBase):
    rank: int
    xp: int
