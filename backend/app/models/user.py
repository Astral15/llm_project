from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.security import hash_password, verify_password

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    images = relationship("Image", back_populates="user")

    # methods
    @classmethod
    def create(cls, db, username: str, password: str) -> "User":
        if db.query(cls).filter(cls.username == username).first():
            raise ValueError("Username already registered")
        u = cls(username=username, password_hash=hash_password(password))
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    def verify(self, password: str) -> bool:
        return verify_password(password, self.password_hash)
