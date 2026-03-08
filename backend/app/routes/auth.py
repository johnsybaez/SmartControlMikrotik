"""Authentication routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
import pyotp
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    decrypt_secret,
    encrypt_secret,
    generate_csrf_token,
    get_current_user_payload,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User, UserMFA

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    otp_code: str | None = Field(default=None, min_length=6, max_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    csrf_token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    email: str | None
    role: str
    is_active: bool


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MFAEnableRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=8)


def _set_auth_cookies(response: Response, access_token: str, csrf_token: str) -> None:
    max_age = settings.JWT_EXPIRATION_MINUTES * 60
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="strict",
        max_age=max_age,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, response: Response, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        logger.warning("login_failed", username=credentials.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    if not user.is_active:
        logger.warning("login_inactive_user", username=credentials.username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    mfa = db.query(UserMFA).filter(UserMFA.user_id == user.id, UserMFA.enabled == True).first()
    if user.role == "admin" and mfa:
        if not credentials.otp_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere codigo MFA")
        secret = decrypt_secret(mfa.secret_encrypted)
        totp = pyotp.TOTP(secret)
        if not totp.verify(credentials.otp_code, valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Codigo MFA invalido")

    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "idle_timeout_minutes": settings.SESSION_IDLE_TIMEOUT_MINUTES,
    }
    access_token = create_access_token(token_data)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, csrf_token)

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    logger.info("login_success", username=user.username, role=user.role)
    record_audit_event(
        db=db,
        user_id=user.id,
        username=user.username,
        action="login",
        target=user.username,
        result="success",
        extra_data={"mfa_used": bool(mfa)},
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "csrf_token": csrf_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@router.get("/mfa/status")
async def mfa_status(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row = db.query(UserMFA).filter(UserMFA.user_id == user.id).first()
    return {"enabled": bool(row and row.enabled), "required": user.role == "admin"}


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar MFA")

    secret = pyotp.random_base32()
    otpauth_uri = pyotp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=settings.MFA_ISSUER_NAME)

    row = db.query(UserMFA).filter(UserMFA.user_id == user.id).first()
    if not row:
        row = UserMFA(user_id=user.id, secret_encrypted=encrypt_secret(secret), enabled=False)
        db.add(row)
    else:
        row.secret_encrypted = encrypt_secret(secret)
        row.enabled = False

    db.commit()
    return {"secret": secret, "otpauth_uri": otpauth_uri}


@router.post("/mfa/enable")
async def enable_mfa(data: MFAEnableRequest, payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row = db.query(UserMFA).filter(UserMFA.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=400, detail="Primero debes ejecutar setup MFA")

    secret = decrypt_secret(row.secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.otp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Codigo MFA invalido")

    row.enabled = True
    db.commit()

    record_audit_event(
        db=db,
        user_id=user.id,
        username=user.username,
        action="mfa_enabled",
        target=user.username,
        result="success",
    )

    return {"success": True, "message": "MFA habilitado"}


@router.post("/mfa/disable")
async def disable_mfa(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row = db.query(UserMFA).filter(UserMFA.user_id == user.id).first()
    if row:
        row.enabled = False
        db.commit()

    record_audit_event(
        db=db,
        user_id=user.id,
        username=user.username,
        action="mfa_disabled",
        target=user.username,
        result="success",
    )

    return {"success": True, "message": "MFA deshabilitado"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user
