"""Rutas de autenticación"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.db.database import get_db
from app.db.models import User
from app.core.security import verify_password, create_access_token, get_current_user_payload
from app.core.logging import get_logger
from app.core.audit import record_audit_event

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    email: str | None
    role: str
    is_active: bool


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login y generación de JWT token"""
    
    # Buscar usuario
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        logger.warning("login_failed", username=credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    
    if not user.is_active:
        logger.warning("login_inactive_user", username=credentials.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    # Generar token
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
    }
    
    access_token = create_access_token(token_data)
    
    # Actualizar last_login
    user.last_login = datetime.utcnow()
    db.commit()
    
    logger.info("login_success", username=user.username, role=user.role)

    record_audit_event(
        db=db,
        user_id=user.id,
        username=user.username,
        action="login",
        target=user.username,
        result="success"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db)
):
    """Obtiene datos del usuario actual"""
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    
    return user
