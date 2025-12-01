from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_username(db: Session, username: str) -> Optional[User]:
  return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, password: str) -> User:
  # single source of truth for user creation if you want to decouple later
  if get_user_by_username(db, username):
    raise ValueError("Username already registered")
  u = User(username=username, password_hash=hash_password(password))
  db.add(u)
  db.commit()
  db.refresh(u)
  return u


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
  u = get_user_by_username(db, username)
  if not u:
    return None
  if not verify_password(password, u.password_hash):
    return None
  return u
