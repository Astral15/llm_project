from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class LLMRequest(Base):
    __tablename__ = "llm_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    prompt = Column(String, nullable=False)
    field_structure = Column(JSON, nullable=False)  # list of {name, type}
    image_id = Column(Integer, ForeignKey("images.id"), nullable=True)

    cache_key = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    image = relationship("Image")


class LLMResponse(Base):
    __tablename__ = "llm_responses"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("llm_requests.id"), nullable=False)

    raw_response = Column(JSON, nullable=False)
    validated_response = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("LLMRequest", backref="responses")
