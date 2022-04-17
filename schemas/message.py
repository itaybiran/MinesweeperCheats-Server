from enum import Enum

from pydantic import BaseModel


class MessageTypeEnum(str, Enum):
    chat_message = 'chat_message'
    opponent_data = 'opponent_data'
    points = 'points'
    board = 'board'
    init_board = 'init_board'
    error = 'error'
    win_or_lose = 'win_or_lose'
    new_xp = 'new_xp'
    time = 'time'


class Message(BaseModel):
    data: str
    type: MessageTypeEnum
