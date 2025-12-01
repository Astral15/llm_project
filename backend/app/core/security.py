from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(pw: str) -> str:
    return _pwd.hash(pw)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> str:
    s = get_settings()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": sub, "exp": expire}, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET_KEY, algorithms=[s.JWT_ALGORITHM])
