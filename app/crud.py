from sqlalchemy.orm import Session
from . import models, schemas, auth



# User CRUD
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Project CRUD (повний CRUD для цієї сутності)
def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects(db: Session, skip: int = 0, limit: int = 100, active_only: bool = False):
    query = db.query(models.Project)
    if active_only:
        query = query.filter(models.Project.is_active == True)
    return query.order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate):
    db_project = get_project(db, project_id)
    if not db_project:
        return None
    update_data = project_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int):
    db_project = get_project(db, project_id)
    if not db_project:
        return None
    # Потрібно вирішити, що робити з пожертвами, якщо видаляється проєкт
    # Наприклад, видалити пов'язані пожертви або заборонити видалення, якщо є пожертви
    # Для простоти, поки що просто видаляємо проєкт
    db.delete(db_project)
    db.commit()
    return db_project


# Donation CRUD
def create_donation(db: Session, donation: schemas.DonationCreate, user_id: int):
    db_donation = models.Donation(**donation.dict(), user_id=user_id)

    # Оновлюємо current_amount в проєкті
    project = get_project(db, donation.project_id)
    if project:
        project.current_amount += donation.amount
        db.add(project)  # SQLAlchemy відстежить зміни
    else:  # Якщо проєкт не знайдено, це помилка
        return None

    db.add(db_donation)
    db.commit()
    db.refresh(db_donation)
    return db_donation


def get_donations_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Donation).filter(models.Donation.user_id == user_id) \
        .order_by(models.Donation.donation_date.desc()).offset(skip).limit(limit).all()


def get_donations_for_project(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Donation).filter(models.Donation.project_id == project_id) \
        .order_by(models.Donation.donation_date.desc()).offset(skip).limit(limit).all()


def get_all_donations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Donation).order_by(models.Donation.donation_date.desc()).offset(skip).limit(limit).all()