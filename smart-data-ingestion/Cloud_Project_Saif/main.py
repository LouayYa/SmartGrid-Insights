import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from routes import router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ingestion")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # SQLite (dev/test fallback) gets its schema from the models directly;
    # Postgres schema is managed by Alembic migrations (alembic upgrade head).
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response

# CORS — permissive for development. Tighten in production.
# Note: wildcard origins cannot be combined with credentials per the CORS spec.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(router)
