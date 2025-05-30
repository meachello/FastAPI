from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from typing import Optional, List

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user_optional, get_current_admin_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- HTML Endpoints for Projects ---

@router.get("/", response_class=HTMLResponse)
async def list_projects_html(
        request: Request,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user_optional)
):
    projects = crud.get_projects(db, active_only=True)  # Показуємо тільки активні на головній
    return templates.TemplateResponse("projects_list.html", {
        "request": request,
        "projects": projects,
        "current_user": current_user,
        "is_admin_page": False  # Для відображення адмін-контролів
    })


@router.get("/all", response_class=HTMLResponse)  # Адмінська сторінка всіх проєктів
async def list_all_projects_admin_html(
        request: Request,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    projects = crud.get_projects(db)  # Адмін бачить всі
    return templates.TemplateResponse("projects_list.html", {
        "request": request,
        "projects": projects,
        "current_user": current_user,
        "is_admin_page": True
    })


@router.get("/new", response_class=HTMLResponse)  # Create - GET form
async def new_project_form_html(request: Request, current_user: models.User = Depends(get_current_admin_user)):
    return templates.TemplateResponse("project_form.html", {
        "request": request,
        "current_user": current_user,
        "project": None,  # Для нової форми
        "form_action_url": "/projects/new"
    })


@router.post("/new", response_class=HTMLResponse)  # Create - POST data
async def create_project_html(
        request: Request,
        name: str = Form(...),
        description: Optional[str] = Form(None),
        target_amount: float = Form(...),
        is_active: bool = Form(True),  # За замовчуванням активний
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    if target_amount <= 0:
        return templates.TemplateResponse("project_form.html", {
            "request": request, "current_user": current_user, "project": None,
            "form_action_url": "/projects/new",
            "error": "Target amount must be positive."
        }, status_code=status.HTTP_400_BAD_REQUEST)

    project_in = schemas.ProjectCreate(
        name=name,
        description=description,
        target_amount=target_amount,
        is_active=is_active
    )
    project = crud.create_project(db=db, project=project_in)
    return RedirectResponse(url=f"/projects/{project.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{project_id}", response_class=HTMLResponse)  # Read one
async def read_project_html(
        request: Request,
        project_id: int = Path(..., gt=0),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user_optional)
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Якщо проєкт неактивний і користувач не адмін, не показуємо
    if not project.is_active and (not current_user or current_user.role != 'admin'):
        raise HTTPException(status_code=404, detail="Project not found or not active")

    donations = crud.get_donations_for_project(db, project_id=project_id, limit=20)
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
        "donations": donations,
        "current_user": current_user
    })


@router.get("/{project_id}/edit", response_class=HTMLResponse)  # Update - GET form
async def edit_project_form_html(
        request: Request,
        project_id: int = Path(..., gt=0),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse("project_form.html", {
        "request": request,
        "project": project,
        "current_user": current_user,
        "form_action_url": f"/projects/{project_id}/edit"
    })


@router.post("/{project_id}/edit", response_class=HTMLResponse)  # Update - POST data
async def update_project_html(
        request: Request,
        project_id: int = Path(..., gt=0),
        name: str = Form(...),
        description: Optional[str] = Form(None),
        target_amount: float = Form(...),
        is_active: bool = Form(False),  # Якщо checkbox не відмічений, False
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    project_db = crud.get_project(db, project_id=project_id)
    if not project_db:
        raise HTTPException(status_code=404, detail="Project not found")

    if target_amount <= 0:
        return templates.TemplateResponse("project_form.html", {
            "request": request, "current_user": current_user, "project": project_db,
            "form_action_url": f"/projects/{project_id}/edit",
            "error": "Target amount must be positive."
        }, status_code=status.HTTP_400_BAD_REQUEST)

    project_update_data = schemas.ProjectUpdate(
        name=name,
        description=description,
        target_amount=target_amount,
        is_active=is_active
    )

    updated_project = crud.update_project(db=db, project_id=project_id, project_update=project_update_data)
    if not updated_project:  # Додаткова перевірка, хоча вище вже є
        raise HTTPException(status_code=404, detail="Project not found during update")

    return RedirectResponse(url=f"/projects/{updated_project.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{project_id}/delete", response_class=HTMLResponse)  # Delete
async def delete_project_html(
        request: Request,  # Не використовується, але FastAPI може вимагати
        project_id: int = Path(..., gt=0),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Перевірка наявності пожертв перед видаленням (опціонально, але гарна практика)
    donations_for_project = crud.get_donations_for_project(db, project_id=project_id, limit=1)
    if donations_for_project:
        # Не дозволяємо видалення, якщо є пожертви. Можна перенаправити з повідомленням про помилку.
        # Або деактивувати проєкт замість видалення.
        # Для простоти, поки що перенаправимо на сторінку адміна з повідомленням.
        # Це не ідеально, краще показати помилку на сторінці проєкту.
        # Або додати параметр ?error=... до URL
        return RedirectResponse(url="/projects/all?error=Cannot_delete_project_with_donations",
                                status_code=status.HTTP_303_SEE_OTHER)

    crud.delete_project(db=db, project_id=project_id)
    return RedirectResponse(url="/projects/all?message=Project_deleted_successfully",
                            status_code=status.HTTP_303_SEE_OTHER)