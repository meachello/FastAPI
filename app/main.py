from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from typing import List
from .mongo_db import close_mongo_connection, client as mongo_client
from . import models, crud, schemas, auth # <--- ПРАВИЛЬНИЙ РЯДОК
from .database import engine, get_db, SessionLocal
from .dependencies import get_current_user_optional, get_current_admin_user, get_current_user
from .routers import auth_router, projects_router, donations_router  # users_router (якщо є)

load_dotenv()

# Створюємо таблиці в БД (зазвичай для цього використовують Alembic)
# models.Base.metadata.create_all(bind=engine) # Робимо це один раз при старті

app = FastAPI(
    title="Система Добровільних Пожертв",
    description="RESTfull API для управління пожертвами медичній установі. Контент генерується на сервері.",
    version="1.0.0",
    openapi_tags=[
        {"name": "HTML Pages", "description": "Endpoints that return HTML content"},
        {"name": "Authentication", "description": "User authentication and registration (HTML & API)"},
        {"name": "Projects", "description": "Managing donation projects (CRUD for Admin via HTML & API)"},
        {"name": "Donations", "description": "Making and viewing donations (HTML & API)"},
        {"name": "Users", "description": "User management (Admin only, API)"}
    ]
)


# Створення таблиць (якщо їх немає) та початкового адміна
def create_initial_data():
    db = SessionLocal()
    try:
        # Створення таблиць
        models.Base.metadata.create_all(bind=engine)

        # Створення адміна, якщо його немає
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "adminpassword")

        admin_user = crud.get_user_by_email(db, email=admin_email)
        if not admin_user:
            user_in = schemas.UserCreate(
                email=admin_email,
                password=admin_password,
                full_name="Admin User",
                role="admin"
            )
            crud.create_user(db=db, user=user_in)
            print(f"Admin user {admin_email} created with password {admin_password}")
        else:
            print(f"Admin user {admin_email} already exists.")

    finally:
        db.close()


# Викликаємо функцію при старті додатку
create_initial_data()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Підключення роутерів
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(projects_router.router, prefix="/projects", tags=["Projects"])
app.include_router(donations_router.router, prefix="/donations", tags=["Donations"])


# app.include_router(users_router.router, prefix="/users", tags=["Users"]) # Якщо буде окремий роутер для користувачів

@app.get("/", response_class=HTMLResponse, tags=["HTML Pages"])
async def read_root(request: Request, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user_optional)):
    projects = crud.get_projects(db, active_only=True, limit=10)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": projects,
        "current_user": current_user
    })


@app.get("/admin", response_class=HTMLResponse, tags=["HTML Pages"])
async def admin_dashboard(request: Request, current_user: models.User = Depends(get_current_admin_user)):
    # Адмін може бачити статистику або мати швидкі посилання
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "current_user": current_user})


# OpenAPI документація (для JSON API частини, якщо вона буде)
# Наприклад, CRUD для проєктів (API частина)
# Ці ендпоінти не будуть використовуватися для HTML, але можуть бути корисні для тестування або майбутнього API
@app.post("/api/projects/", response_model=schemas.Project, tags=["Projects API (Admin Only)"],
          status_code=status.HTTP_201_CREATED)
def create_project_api(project: schemas.ProjectCreate, db: Session = Depends(get_db),
                       current_user: models.User = Depends(
                           auth.get_current_admin_user)):  # Використовуємо інший get_current_admin_user для API
    return crud.create_project(db=db, project=project)


@app.get("/api/projects/", response_model=List[schemas.Project], tags=["Projects API (Public)"])
def read_projects_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db), active_only: bool = True):
    projects = crud.get_projects(db, skip=skip, limit=limit, active_only=active_only)
    return projects


# ... і так далі для інших API ендпоінтів, якщо потрібно

# Приклад для OpenAPI (можна додати більше)
@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(
        current_user: models.User = Depends(auth.get_current_user_api)):  # Використовуємо API версію get_current_user
    # Тут можна додати логіку, хто може бачити документацію
    # Наприклад, тільки адміни
    # if not current_user or current_user.role != "admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return app.openapi()

@app.on_event("startup")
async def startup_event():
    try:
        # Перевірка підключення до MongoDB
        await mongo_client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
    # Тут можна додати create_initial_data() для SQL, якщо потрібно
    create_initial_data()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("MongoDB connection closed.")