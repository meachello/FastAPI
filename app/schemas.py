from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: str = "user" # Default role

class UserUpdate(UserBase):
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    role: str
    is_active: bool

    class Config:
        orm_mode = True

# Project Schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: float
    is_active: bool = True

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    is_active: Optional[bool] = None


class Project(ProjectBase):
    id: int
    current_amount: float
    created_at: datetime
    # donations: List['Donation'] = [] # Щоб уникнути циклічної залежності, можна так

    class Config:
        orm_mode = True

# Donation Schemas
class DonationBase(BaseModel):
    amount: float
    message: Optional[str] = None

class DonationCreate(DonationBase):
    project_id: int

class Donation(DonationBase):
    id: int
    donation_date: datetime
    user_id: int
    project_id: int
    donor: Optional[User] = None # Для відображення інформації про донора
    project: Optional[ProjectBase] = None # Для відображення інформації про проєкт

    class Config:
        orm_mode = True

# Token Schemas (for auth.py)
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Для форм HTML
class LoginForm(BaseModel):
    username: EmailStr # email as username
    password: str

class ActivityLogBase(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_email: Optional[str] = None # Або user_id
    action: str # Наприклад, "LOGIN", "CREATE_PROJECT", "MAKE_DONATION"
    details: Optional[dict[str, Any]] = None # Додаткова інформація

class ActivityLogInDB(ActivityLogBase):
    id: str = Field(alias="_id") # MongoDB використовує _id

    class Config:
        orm_mode = True
        populate_by_name = True # Дозволяє використовувати _id як id
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }