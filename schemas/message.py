from enum import Enum

from pydantic import BaseModel


class MessageTypeEnum(str, Enum):
    chat_message = 'chat_message'
    opponent_data = 'opponent_data'
    points = 'points'
    time = 'time'


class Message(BaseModel):
    data: str
    type: MessageTypeEnum
