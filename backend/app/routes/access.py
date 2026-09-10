from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.group_member import GroupMember
from app.auth import can_manage_person
from app.schemas.user import UserCreate

router = APIRouter()

@router.get('/auth/me')
def me(db: Session = Depends(get_db)):
    if db.info.get('local_development'):
        owner = db.query(User).join(GroupMember, GroupMember.user_id == User.id).filter(GroupMember.role == 'owner').order_by(User.id).first()
        return dict(id=owner.id if owner else 0, name=owner.name if owner else 'Organizador local', local_development=True)
    user = db.info['actor']
    return dict(id=user.id, name=user.name, email=user.login_email)

class MemberAccess(BaseModel):
    can_register_expenses: bool
    login_email: str | None = Field(default=None, max_length=320)

@router.put('/group-members/group/{group_id}/access/{user_id}')
def update_access(group_id: int, user_id: int, data: MemberAccess, db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    user = db.get(User, user_id)
    if not member or not user:
        raise HTTPException(404, 'Member not found')
    if member.role == 'owner':
        raise HTTPException(409, 'Organizer access cannot be changed')
    email = data.login_email.strip().lower() if data.login_email else None
    if email:
        try:
            UserCreate(name=user.name, email=email)
        except ValidationError:
            raise HTTPException(422, 'Invalid email') from None
    if email != user.login_email:
        if not can_manage_person(db, db.info['actor'], user):
            raise HTTPException(409, 'Linked account cannot be reassigned')
        user.login_email = email
    if data.can_register_expenses and not user.login_email:
        raise HTTPException(422, 'Access email required')
    member.can_register_expenses = data.can_register_expenses
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Access email already linked') from None
    return dict(id=member.id, user_id=user.id, can_register_expenses=member.can_register_expenses)
