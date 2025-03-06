from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from app.routers import embed

app = FastAPI()

app.include_router(embed.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        content={"ok": False, "message": str(exc.detail)}, status_code=exc.status_code
    )

@app.get("/", tags=["health"])
def index():
    return {"ok": True, "message": "Service is healthy"}