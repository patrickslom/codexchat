from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from sqlalchemy import text

from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast when the configured database is unreachable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    yield


app = FastAPI(title="CodexChat API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_probe(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close(code=1000)
