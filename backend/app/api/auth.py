from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    username: str
    password: str
    password_confirm: str

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str

def _auth_err() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        username: Optional[str] = payload.get("sub")
        if not username:
            raise _auth_err()
    except JWTError:
        raise _auth_err()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise _auth_err()
    return user

@router.post("/register", response_model=UserRead, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.password != user_in.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        user = User.create(db, username=user_in.username, password=user_in.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return user

@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not user.verify(form.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    s = get_settings()
    exp = timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(user.username, exp)
    return Token(access_token=token)
    
@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
