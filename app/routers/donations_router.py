from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from typing import Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, get_current_admin_user, get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/make/{project_id}", response_class=HTMLResponse)
async def make_donation_form_html(
        request: Request,
        project_id: int = Path(..., gt=0),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)  # Потрібен залогінений юзер
):
    project = crud.get_project(db, project_id=project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Active project not found")

    return templates.TemplateResponse("make_donation.html", {
        "request": request,
        "project": project,
        "current_user": current_user
    })


@router.post("/make/{project_id}", response_class=HTMLResponse)
async def handle_make_donation_html(
        request: Request,
        project_id: int = Path(..., gt=0),
        amount: float = Form(...),
        message: Optional[str] = Form(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Active project not found for donation")

    if amount <= 0:
        return templates.TemplateResponse("make_donation.html", {
            "request": request, "project": project, "current_user": current_user,
            "error": "Donation amount must be positive."
        }, status_code=status.HTTP_400_BAD_REQUEST)

    donation_in = schemas.DonationCreate(project_id=project_id, amount=amount, message=message)
    donation = crud.create_donation(db=db, donation=donation_in, user_id=current_user.id)

    if not donation:  # Якщо create_donation повернув None (наприклад, проєкт не знайдено при оновленні)
        raise HTTPException(status_code=500, detail="Could not process donation")

    # Перенаправлення на сторінку проєкту з повідомленням про успішну пожертву
    return RedirectResponse(url=f"/projects/{project.id}?donation_success=true", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/my", response_class=HTMLResponse)
async def my_donations_html(
        request: Request,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    donations = crud.get_donations_by_user(db, user_id=current_user.id)
    return templates.TemplateResponse("my_donations.html", {
        "request": request,
        "donations": donations,
        "current_user": current_user
    })


@router.get("/all", response_class=HTMLResponse)  # Тільки для адміна
async def all_donations_admin_html(
        request: Request,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    donations = crud.get_all_donations(db)
    return templates.TemplateResponse("admin/all_donations.html", {
        "request": request,
        "donations": donations,
        "current_user": current_user
    })