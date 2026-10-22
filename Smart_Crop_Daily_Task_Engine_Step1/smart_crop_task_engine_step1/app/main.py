from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.init_db import init_db
from app.services.daily_task_scheduler import (
    start_daily_task_scheduler,
    stop_daily_task_scheduler,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    start_daily_task_scheduler()
    try:
        yield
    finally:
        stop_daily_task_scheduler()


app = FastAPI(
    title="Smart Crop Advisory API",
    description="Agricultural knowledge base for tomato and chilli",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def home():
    return {"name": "Smart Crop Advisory API", "status": "running", "version": "0.2.0"}


@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}
