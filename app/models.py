from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user") # "user" or "admin"
    is_active = Column(Boolean, default=True)

    donations = relationship("Donation", back_populates="donor")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    donations = relationship("Donation", back_populates="project")

class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    donation_date = Column(DateTime(timezone=True), server_default=func.now())
    message = Column(String(500), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))

    donor = relationship("User", back_populates="donations")
    project = relationship("Project", back_populates="donations")