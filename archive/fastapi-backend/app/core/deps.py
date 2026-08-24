from __future__ import annotations
from typing import Annotated, Iterable

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.core.config import get_settings
from app.db.session import get_db
from app.models.users import User
from app.models.roles import Role, UserRole


bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_request(request: Request) -> str | None:
    """Extract token from HttpOnly cookie or Authorization header."""
    # Try HttpOnly cookie first (more secure)
    access_token = request.cookies.get("access_token")
    if access_token:
        return access_token
    
    # Fallback to Authorization header (backward compatibility)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    user = db.query(User).filter(User.email == sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user


def require_roles(*allowed: str):
    def _dep(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> User:
        if not allowed:
            return user
        # fetch user roles
        q = (
            db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user.id)
        )
        user_roles = {name for (name,) in q.all()}
        if user_roles.intersection(set(allowed)):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    return _dep
