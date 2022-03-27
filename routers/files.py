from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter(
    prefix="/files"
)


@router.get("/winmine")
async def winmine_game():
    return FileResponse("htmlpage/files/winmine.html")


@router.get("/background")
async def winmine_game():
    return FileResponse("htmlpage/icons/background.png")
