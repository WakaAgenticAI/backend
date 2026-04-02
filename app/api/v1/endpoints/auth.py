from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, verify_password, decode_token
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.users import User
from app.models.roles import Role, UserRole

router = APIRouter()

settings = get_settings()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db), response: Response = Response) -> JSONResponse:
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status and user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
    
    sub = user.email
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)
    
    # Set HttpOnly cookies for production security
    is_secure = settings.APP_ENV == "prod"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    # Still return tokens for backward compatibility (localStorage fallback)
    return JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "message": "Login successful"
    })


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/auth/refresh")
def refresh_token(data: RefreshIn, response: Response = Response) -> JSONResponse:
    # For simplicity, accept any provided refresh token subject and mint a new pair later we should verify type="refresh"
    # Proper validation and revocation list to be added with DB-backed sessions
    from app.core.security import decode_token

    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")
    
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)
    
    # Update HttpOnly cookies
    is_secure = settings.APP_ENV == "prod"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "message": "Token refreshed successfully"
    })


@router.post("/auth/logout")
def logout(response: Response = Response) -> JSONResponse:
    """Clear authentication cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return JSONResponse(content={"message": "Logged out successfully"})


class MeOut(BaseModel):
    email: str
    full_name: str | None = None
    status: str | None = None
    roles: list[str] = []


@router.get("/auth/me", response_model=MeOut)
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch roles for the user
    role_names = [
        name
        for (name,) in db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    ]
    return MeOut(
        email=user.email,
        full_name=getattr(user, "full_name", None),
        status=getattr(user, "status", None),
        roles=role_names,
    )
