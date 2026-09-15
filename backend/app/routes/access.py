from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.group_member import GroupMember
from app.auth import can_manage_person
from app.schemas.user import UserCreate
from app.models.group import Group
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from sqlalchemy import or_

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
    if member.access_user_id:
        linked = db.get(User, member.access_user_id)
        if email != linked.login_email:
            raise HTTPException(409, 'Linked account cannot be reassigned')
    elif email != user.login_email:
        if not can_manage_person(db, db.info['actor'], user):
            raise HTTPException(409, 'Linked account cannot be reassigned')
        user.login_email = email
    if data.can_register_expenses and not user.login_email and not member.access_user_id:
        raise HTTPException(422, 'Access email required')
    member.can_register_expenses = data.can_register_expenses
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Access email already linked') from None
    return dict(id=member.id, user_id=user.id, can_register_expenses=member.can_register_expenses)

@router.post('/group-members/group/{group_id}/access/{user_id}/invitation')
def create_invitation(group_id: int, user_id: int, db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    user = db.get(User, user_id)
    if not member or not user:
        raise HTTPException(404, 'Member not found')
    if member.role == 'owner' or member.access_user_id or user.auth_subject or user.login_email:
        raise HTTPException(409, 'Member already has access')
    token = secrets.token_urlsafe(32)
    member.invite_hash = hashlib.sha256(token.encode()).hexdigest()
    member.invite_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    db.commit()
    return dict(id=member.id, token=token, expires_at=member.invite_expires.isoformat() + 'Z')

@router.delete('/group-members/group/{group_id}/access/{user_id}/invitation')
def cancel_invitation(group_id: int, user_id: int, db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if not member:
        raise HTTPException(404, 'Member not found')
    member.invite_hash = None
    member.invite_expires = None
    db.commit()
    return {'cancelled': True}

class InvitationToken(BaseModel):
    token: str = Field(min_length=40, max_length=100)

def pending_invitation(data, db):
    member = db.query(GroupMember).filter_by(invite_hash=hashlib.sha256(data.token.encode()).hexdigest()).first()
    if not member or not member.invite_expires or member.invite_expires <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(409, 'Invitation unavailable')
    user = db.get(User, member.user_id)
    if member.role == 'owner' or member.access_user_id or user.auth_subject or user.login_email:
        raise HTTPException(409, 'Invitation unavailable')
    return member

@router.post('/invitations/preview')
def preview_invitation(data: InvitationToken, db: Session = Depends(get_db)):
    member = pending_invitation(data, db)
    return dict(id=member.id, person=db.get(User, member.user_id).name,
                trip=db.get(Group, member.group_id).name)

@router.post('/invitations/accept')
def accept_invitation(data: InvitationToken, db: Session = Depends(get_db)):
    member = pending_invitation(data, db)
    actor = db.info['actor']
    if db.query(GroupMember).filter(GroupMember.group_id == member.group_id,
            or_(GroupMember.user_id == actor.id, GroupMember.access_user_id == actor.id)).first():
        raise HTTPException(409, 'Already in invited trip')
    try:
        changed = db.query(GroupMember).filter_by(id=member.id, invite_hash=member.invite_hash,
            access_user_id=None).filter(GroupMember.invite_expires > datetime.now(timezone.utc).replace(tzinfo=None)).update(
            dict(access_user_id=actor.id, invite_hash=None, invite_expires=None, can_register_expenses=False), synchronize_session=False)
        if not changed:
            raise HTTPException(409, 'Invitation unavailable')
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Already in invited trip') from None
    return dict(id=member.id, group_id=member.group_id)
