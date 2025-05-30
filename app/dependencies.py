from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from . import  crud, models, auth
from .database import get_db


async def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Returns user if logged in, or None otherwise. For public pages that can show user-specific info."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except auth.JWTError:
        return None

    user = crud.get_user_by_email(db, email=email)
    return user


async def get_current_user(current_user_optional: Optional[models.User] = Depends(get_current_user_optional)):
    """Requires user to be logged in. Redirects to login if not."""
    if not current_user_optional:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/auth/login"}
        )
    return current_user_optional


async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        # Можна перенаправити на сторінку "акаунт неактивний" або просто показати помилку
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        # Можна перенаправити на головну з повідомленням про помилку
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user