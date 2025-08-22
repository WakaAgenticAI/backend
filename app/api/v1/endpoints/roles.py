from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import require_roles
from app.models.roles import Role, UserRole
from app.models.users import User
from app.schemas.roles import RoleIn, RoleOut, AssignRoleIn

router = APIRouter()


@router.get("/roles", response_model=list[RoleOut], dependencies=[Depends(require_roles("Admin"))])
def list_roles(db: Session = Depends(get_db)) -> list[RoleOut]:
    roles = db.query(Role).order_by(Role.name.asc()).all()
    return [RoleOut(id=r.id, name=r.name) for r in roles]


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin"))])
def create_role(body: RoleIn, db: Session = Depends(get_db)) -> RoleOut:
    if db.query(Role).filter(Role.name == body.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")
    r = Role(name=body.name)
    db.add(r)
    db.commit()
    db.refresh(r)
    return RoleOut(id=r.id, name=r.name)


@router.post(
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
"/users/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("Admin"))],
    response_class=Response,
)
def assign_role(user_id: int, body: AssignRoleIn, db: Session = Depends(get_db)) -> Response:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = db.query(Role).filter(Role.name == body.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    exists = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
    if exists:
        return Response(status_code=status.HTTP_204_NO_CONTENT)  # idempotent
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users/{user_id}/roles",
    response_model=list[RoleOut],
    dependencies=[Depends(require_roles("Admin"))],
)
def list_user_roles(user_id: int, db: Session = Depends(get_db)) -> list[RoleOut]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    rows = (
        db.query(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .order_by(Role.name.asc())
        .all()
    )
    return [RoleOut(id=r.id, name=r.name) for r in rows]


@router.delete(
    "/users/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("Admin"))],
    response_class=Response,
)
def remove_role(user_id: int, body: AssignRoleIn, db: Session = Depends(get_db)) -> Response:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = db.query(Role).filter(Role.name == body.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    link = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
    if not link:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    db.delete(link)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
