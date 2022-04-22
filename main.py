import asyncio
import json
from asyncio import create_task
from asyncio.log import logger
from functools import wraps
from queue import PriorityQueue
from typing import List, Callable, Optional, Awaitable

import uvicorn
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from constants import *
from crud import user as user_crud
from routers import users
from routers.users import get_db
from schemas import user as user_schemas
from schemas.message import Message, MessageTypeEnum
from utils import calculations
from utils.auth import get_current_user_http, get_current_user_ws
from utils.board_manager import generate_random_board
from utils.priority_entry import PriorityEntry


def repeat_every(*, seconds: float, wait_first: bool = False):
    def decorator(func: Callable[[], Optional[Awaitable[None]]]):
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func)
        async def wrapped():
            async def loop():
                if wait_first:
                    await asyncio.sleep(seconds)
                while True:
                    try:
                        if is_coroutine:
                            await func()
                        else:
                            await run_in_threadpool(func)
                    except Exception as e:
                        logger.error(str(e))
                    await asyncio.sleep(seconds)

            create_task(loop())

        return wrapped

    return decorator


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, nickname: str, message: Message):
        user_to_send = find_user(nickname)
        if user_to_send is not None:
            await user_to_send["ws"].send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


app = FastAPI()
app.include_router(users.router)
manager = ConnectionManager()
connected_users = []
waiting_rooms = [PriorityQueue(), PriorityQueue(), PriorityQueue()]

templates = Jinja2Templates(directory="htmlpage/templates")

app.mount(
    "/static",
    StaticFiles(directory="htmlpage/static"),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/download")
async def download_file():
    return FileResponse("htmlpage/files/README.md", media_type='application/octet-stream', filename="download.md")


@app.get("/download-winmine")
async def download_file():
    return FileResponse("htmlpage/files/Winmine__XP.exe", media_type='application/octet-stream',
                        filename="Winmine__XP.exe")


@app.get("/favicon.ico")
async def get_bomb():
    return FileResponse("htmlpage/icons/bomb.ico")


@app.websocket("/ws")
async def connect(websocket: WebSocket, nickname: str, rank: int, difficulty: int, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    user = {"nickname": nickname, "rank": rank, "difficulty": difficulty, "ws": websocket,
            "opponent_nickname": None, "waiting_time": 0, "init_board": [[]]}
    connected_users.append(user)
    waiting_rooms[difficulty].put(PriorityEntry(user["rank"], user))
    data = ''
    try:
        while True:
            if has_opponent(user):
                await handle_data_request(user, data, db)
            data = await websocket.receive_json()
    except Exception as e:
        print(e)
        await manager.send_personal_message(user["opponent_nickname"], json.dumps(
            {"data": nickname + " was disconnected", "type": "chat_message"}))
        disconnect_user(nickname)


@app.post("/disconnect-ws")
async def get_user_info(user: user_schemas.User = Depends(get_current_user_ws)):
    if user is not None:
        disconnect_user(user.nickname)


@app.post("/disconnect-http")
async def get_user_info(user: user_schemas.User = Depends(get_current_user_http)):
    if user is not None:
        for logged_in_user in users.logged_in_users:
            if user.nickname == logged_in_user["user"].nickname:
                users.logged_in_users.remove(logged_in_user)


async def handle_data_request(user, message: Message, db: Session):
    if message["type"] == MessageTypeEnum.chat_message:
        await manager.send_personal_message(user["opponent_nickname"], json.dumps(message))
    # elif message["type"] == MessageTypeEnum.opponent_data:
    #     await manager.send_json({"data": find_user(user["opponent_nickname"]), "type": "opponent_data"})
    # elif message["type"] == MessageTypeEnum.init_board:
    #     await manager.send_json({"data": user["init_board"], "type": "init_data"})
    elif message["type"] == MessageTypeEnum.points:
        await manager.send_personal_message(user["opponent_nickname"], json.dumps(message))
    elif message["type"] == MessageTypeEnum.board:
        await manager.send_personal_message(user["opponent_nickname"], json.dumps(message))
    elif message["type"] == MessageTypeEnum.win_or_lose:
        await manager.send_personal_message(user["nickname"], json.dumps(message))
        message["data"] = str(1 - int(message["data"]))
        await manager.send_personal_message(user["opponent_nickname"], json.dumps(message))
    elif message["type"] == MessageTypeEnum.new_xp:
        await manager.send_personal_message(user["nickname"],
                                            json.dumps(update_user_rank_and_xp(user, message["data"], db)))


def update_user_rank_and_xp(user, xp, db: Session):
    new_user_info: user_schemas.User = {}
    new_user_info["nickname"] = user["nickname"]
    rank = calculations.calculate_rank(int(xp))
    if int(xp) > 0:
        new_user_info["xp"] = int(xp)
    else:
        new_user_info["xp"] = 0
        rank = 0
    new_user_info["rank"] = rank
    if new_user_info["rank"] > 14:
        new_user_info["rank"] = 14
    user_crud.update_user_info(db, new_user_info)
    return {"data": {"rank": str(new_user_info["rank"]), "xp": str(new_user_info["xp"])}, "type": "new_xp"}


def disconnect_user(nickname):
    """disconnects user"""
    user = find_user(nickname)
    if user is not None:
        connected_users.remove(user)
        manager.disconnect(user["ws"])
        user_in_waiting_room = find_user_in_waiting_room(user)
        if user_in_waiting_room:
            waiting_rooms[user["difficulty"]].queue.remove(user_in_waiting_room)
        if user["opponent_nickname"] is not None:
            opponent = find_user(user["opponent_nickname"])
            opponent["opponent_nickname"] = None
            user["opponent_nickname"] = None


def find_user(nickname):
    """search for user in 'connected_users' by nickname"""
    return next((user for user in connected_users if user["nickname"] == nickname), None)


def find_user_in_waiting_room(user_to_find):
    """search for user in 'waiting_rooms' by nickname"""
    return next((user for user in waiting_rooms[user_to_find["difficulty"]].queue if
                 user.data["nickname"] == user_to_find["nickname"]), None)


def find_opponent(waiting_room):
    """returns the first couple in the waiting room"""
    return waiting_room.get().data, waiting_room.get().data


@app.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
async def match():
    for waiting_room in waiting_rooms:
        if waiting_room.qsize() >= MINIMUM_USERS_IN_WAITING_ROOM:
            (user1, user2) = find_opponent(waiting_room)
            if abs(user1["rank"] - user2["rank"]) <= MAX_RANK_DIFFERENCE or (
                    user1["waiting_time"] > MAX_WAITING_TIME and user2["waiting_time"] > MAX_WAITING_TIME):
                await connect_two_users(user1, user2)
            else:
                waiting_room.put(PriorityEntry(user1["rank"], user1))
                waiting_room.put(PriorityEntry(user2["rank"], user2))
            user1["waiting_time"] += 1
            user2["waiting_time"] += 1
    return None


async def connect_two_users(user1, user2):
    """connecting between two users in a waiting room"""
    generated_board = generate_random_board(user1["difficulty"])
    user1["opponent_nickname"] = user2["nickname"]
    user2["opponent_nickname"] = user1["nickname"]
    user1["init_board"] = generated_board
    user2["init_board"] = generated_board
    user1copy: dict = user1.copy()
    user2copy: dict = user2.copy()
    user1copy["ws"] = None
    user2copy["ws"] = None
    await user1["ws"].send_json(json.dumps({"data": user2copy, "type": "opponent_data"}))
    await user2["ws"].send_json(json.dumps({"data": user1copy, "type": "opponent_data"}))
    await user1["ws"].send_json(json.dumps({"data": generated_board, "type": "init_board"}))
    await user2["ws"].send_json(json.dumps({"data": generated_board, "type": "init_board"}))


def get_opponent_nickname(nickname):
    """returns user's opponent nickname"""
    return find_user(nickname)["opponent_nickname"]


def has_opponent(user):
    """checks if user have an opponent"""
    opponent_nickname = user["opponent_nickname"]
    return opponent_nickname is not None and find_user(opponent_nickname) is not None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
