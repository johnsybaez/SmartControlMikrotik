"""Rutas para gestión de usuarios"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
from app.db.database import get_db
from app.db.models import User
from app.core.security import require_admin, hash_password
from app.core.logging import get_logger
from app.core.audit import record_audit_event

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Literal["admin", "operator"] = "operator"
    is_active: bool = True


class UserUpdate(BaseModel):
    password: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[Literal["admin", "operator"]] = None
    is_active: Optional[bool] = None


class PasswordUpdate(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    is_active: bool
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    users = db.query(User).order_by(User.id.asc()).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nombre de usuario ya existe")

    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        email=user_data.email,
        role=user_data.role,
        is_active=user_data.is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit_event(
        db=db,
        user_id=payload.get("user_id"),
        username=payload.get("sub"),
        action="user_created",
        target=user.username,
        result="success"
    )

    logger.info("user_created", user=user.username, by=payload.get("sub"))
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user_data.password:
        user.password_hash = hash_password(user_data.password)
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    record_audit_event(
        db=db,
        user_id=payload.get("user_id"),
        username=payload.get("sub"),
        action="user_updated",
        target=user.username,
        result="success"
    )

    logger.info("user_updated", user=user.username, by=payload.get("sub"))
    return user


@router.put("/{user_id}/password", response_model=UserResponse)
async def update_user_password(
    user_id: int,
    password_data: PasswordUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.password_hash = hash_password(password_data.new_password)
    db.commit()
    db.refresh(user)

    record_audit_event(
        db=db,
        user_id=payload.get("user_id"),
        username=payload.get("sub"),
        action="user_password_updated",
        target=user.username,
        result="success"
    )

    logger.info("user_password_updated", user=user.username, by=payload.get("sub"))
    return user