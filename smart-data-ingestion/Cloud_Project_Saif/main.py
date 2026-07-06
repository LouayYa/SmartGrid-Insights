from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables on startup (safe no-op if they already exist).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

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
