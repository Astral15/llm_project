from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    storage_key = Column(String, nullable=False)
    url = Column(String, nullable=False)
    content_hash = Column(String, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="images")
