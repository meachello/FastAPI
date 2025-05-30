from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os

from . import crud, models, schemas

from .database import get_db

# Завантажуємо змінні середовища
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-dev")  # CHANGE THIS IN PRODUCTION
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Для HTML форм, tokenUrl буде вказувати на наш API endpoint
# Для API-only, це може бути просто "token"
# Для HTML, ми будемо використовувати куки, але OAuth2PasswordBearer корисний для API-частини
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)  # auto_error=False для HTML


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    token = request.cookies.get("access_token")
    if not token:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="Could not validate credentials",
        headers={"Location": "/auth/login"},  # Redirect to login if token invalid
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None  # Or raise credentials_exception if strict
        token_data = schemas.TokenData(email=email)
    except JWTError:
        return None  # Or raise credentials_exception

    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        return None  # Or raise credentials_exception
    return user


async def get_current_active_user(current_user: Optional[models.User] = Depends(get_current_user_from_cookie)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/auth/login"}
        )
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


# Функція для API (не для HTML форм, хоча може бути використана)
async def get_current_user_api(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:  # Якщо токен не надано (наприклад, для публічних сторінок)
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user_api(current_user: models.User = Depends(get_current_user_api)):
    if not current_user:  # Дозволяє анонімний доступ, якщо endpoint це дозволяє
        return None
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user