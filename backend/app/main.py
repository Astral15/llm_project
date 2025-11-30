from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth
from app.api import images
from app.db.base import Base
from app.db.session import engine

#  add these imports so tables are registered
from app.models.user import User  # noqa: F401
from app.models.image import Image  # noqa: F401

app = FastAPI(title="LLM Structured Output API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # during dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(images.router)
