from sqlalchemy import Column, Integer, String
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rank = Column(Integer, default=0)
    xp = Column(Integer, default=0)

    def __init__(self, nickname, hashed_password):
        self.nickname = nickname
        self.hashed_password = hashed_password
