from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

s = get_settings()

engine = create_engine(s.SQLALCHEMY_DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:  # noqa: E722
        db.rollback()
        raise
    finally:
        db.close()
