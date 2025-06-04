from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app import crud, schemas, auth, models
from app.database import get_db
from app.dependencies import get_current_user_optional, get_current_user
from app.mongo_crud import add_activity_log # Імпортуємо функцію
from app.schemas import ActivityLogBase # Імпортуємо схему

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, current_user: models.User = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("register.html", {"request": request, "current_user": None})


@router.post("/register", response_class=HTMLResponse)
async def handle_registration(
        request: Request,
        email: EmailStr = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=email)
    if user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "current_user": None,
            "error": "Email already registered"
        })

    user_create = schemas.UserCreate(email=email, password=password, full_name=full_name)
    crud.create_user(db=db, user=user_create)

    # Можна одразу логінити або перенаправляти на сторінку логіна з повідомленням
    return RedirectResponse(url="/auth/login?message=Registration successful. Please login.",
                            status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, message: Optional[str] = None,
                     current_user: models.User = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "message": message, "current_user": None})


@router.post("/login")  # Не HTMLResponse, бо він встановлює куку і редіректить
async def handle_login(
        request: Request,
        username: EmailStr = Form(...),  # FastAPI використовує username з OAuth2PasswordRequestForm
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=username)
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "current_user": None,
            "error": "Incorrect email or password"
        }, status_code=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "current_user": None,
            "error": "User account is inactive"
        }, status_code=status.HTTP_400_BAD_REQUEST)

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    await add_activity_log(ActivityLogBase(user_email=user.email, action="LOGIN_SUCCESS"))
    response.set_cookie(key="access_token", value=f"{access_token}", httponly=True, max_age=1800,
                        samesite="Lax")  # max_age в секундах
    return response


@router.get("/logout")
async def logout_user(request: Request, current_user: models.User = Depends(get_current_user)):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


# API endpoint for token generation (useful for Postman/Swagger or JS clients)
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token_api(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}