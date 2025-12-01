from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, images, llm
from app.db.base import Base
from app.db.session import engine

# import models so they register with Base
from app.models.user import User  # noqa: F401
from app.models.image import Image  # noqa: F401
from app.models.llm import LLMRequest, LLMResponse  # noqa: F401

app = FastAPI(title="LLM Structured Output API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth.router)
app.include_router(images.router)
app.include_router(llm.router)
