import asyncio
from asyncio import create_task
from asyncio.log import logger
from functools import wraps
from queue import PriorityQueue
from typing import List, Callable, Optional, Awaitable

import uvicorn
from fastapi import FastAPI, WebSocket, Depends
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, HTMLResponse
from starlette.websockets import WebSocketDisconnect
from utils.priority_entry import PriorityEntry

from schemas import user as user_schemas
from utils.auth import get_current_user

from routers import users, files
from constants import *


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

    async def send_personal_message(self, nickname: str, message: str):
        user_to_send = find_user(nickname)
        if user_to_send is not None:
            await user_to_send["ws"].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


app = FastAPI()
app.include_router(users.router)
app.include_router(files.router)
manager = ConnectionManager()
connected_users = []
waiting_rooms = [PriorityQueue(), PriorityQueue(), PriorityQueue()]


@app.get("/", response_class=HTMLResponse)
async def get_home_page():
    return """
        <htmlpage>
        <head>
            <title>Winmine Project</title>
            <link rel="icon" href="http://localhost:8000/favicon.ico" type="image/x-icon">
        </head>
        <body>
                <div style="position: relative; top:75px;">
                    <iframe style="position: relative; left: 75px;" title="winmine demo" src="http://localhost:8000/files/winmine" height="275px" width="180px"></iframe>
                    <br>
                    <a style="position: relative; left: 115px;" href="http://localhost:8000/download">download here!</a>
            </div>
        </body>
    </htmlpage>
    """


@app.get("/download")
async def download_file():
    return FileResponse("htmlpage/files/README.md", media_type='application/octet-stream', filename="download.md")


@app.get("/favicon.ico")
async def get_bomb():
    return FileResponse("htmlpage/icons/bomb.ico")


@app.websocket("/ws")
async def connect(websocket: WebSocket, nickname, rank: int, difficulty: int):
    await manager.connect(websocket)
    user = {"nickname": nickname, "rank": rank, "difficulty": difficulty, "ws": websocket, "opponent_nickname": None, "waiting_time": 0}
    connected_users.append(user)
    waiting_rooms[difficulty].put(PriorityEntry(user["rank"], user))
    data = ''
    try:
        while True:
            if has_opponent(nickname):
                await manager.send_personal_message(get_opponent_nickname(nickname), data)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.send_personal_message(get_opponent_nickname(nickname), nickname + " was disconnected")
        disconnect_user(nickname)


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
            find_user(user["opponent_nickname"])["opponent_nickname"] = None
            user["opponent_nickname"] = None


def find_user(nickname):
    """search for user in 'connected_users' by nickname"""
    return next((user for user in connected_users if user["nickname"] == nickname), None)


def find_user_in_waiting_room(user_to_find):
    """search for user in 'waiting_rooms' by nickname"""
    return next((user for user in waiting_rooms[user_to_find["difficulty"]].queue if user.data["nickname"] == user_to_find["nickname"]), None)


def find_opponent(waiting_room):
    """returns the first couple in the waiting room"""
    return waiting_room.get().data, waiting_room.get().data


@app.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
async def match():
    for waiting_room in waiting_rooms:
        if waiting_room.qsize() >= MINIMUM_USERS_IN_WAITING_ROOM:
            (user1, user2) = find_opponent(waiting_room)
            if abs(user1["rank"] - user2["rank"]) <= MAX_RANK_DIFFERENCE or (user1["waiting_time"] > MAX_WAITING_TIME and user2["waiting_time"] > MAX_WAITING_TIME):
                await connect_two_users(user1, user2)
            else:
                waiting_room.put(PriorityEntry(user1["rank"], user1))
                waiting_room.put(PriorityEntry(user2["rank"], user2))
            user1["waiting_time"] += 1
            user2["waiting_time"] += 1
    return None


async def connect_two_users(user1, user2):
    """connecting between two users in a waiting room"""
    user1["opponent_nickname"] = user2["nickname"]
    user2["opponent_nickname"] = user1["nickname"]
    await user1["ws"].send_text(user2["nickname"] + " is connected")
    await user2["ws"].send_text(user1["nickname"] + " is connected")


def get_opponent_nickname(nickname):
    """returns user's opponent nickname"""
    return find_user(nickname)["opponent_nickname"]


def has_opponent(nickname):
    """checks if user have an opponent"""
    opponent_nickname = get_opponent_nickname(nickname)
    return opponent_nickname is not None and find_user(opponent_nickname) is not None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
