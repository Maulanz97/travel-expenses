from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from app.schemas.user import UserCreate
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.models.payment import Payment
from sqlalchemy import or_
from app.schemas.group_member import GroupMemberCreate


router = APIRouter(
    prefix="/group-members",
    tags=["Group Members"]
)

@router.delete('/group/{group_id}/people/{user_id}')
def remove_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    if not db.get(Group, group_id):
        raise HTTPException(404, 'Group not found')
    members = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).all()
    if any(member.role == 'owner' for member in members):
        raise HTTPException(409, 'Organizer cannot be removed')
    if not members:
        return {'removed': True}
    # Include voided records: they can be restored and still need their members.
    participant = db.query(ExpenseParticipant).join(
        Expense, Expense.id == ExpenseParticipant.expense_id
    ).filter(Expense.group_id == group_id, ExpenseParticipant.user_id == user_id).first()
    payer = any(
        expense.payer_id == user_id or str(user_id) in (expense.payer_contributions or {})
        for expense in db.query(Expense).filter_by(group_id=group_id)
    )
    payment = db.query(Payment).filter(
        Payment.group_id == group_id,
        or_(Payment.from_user_id == user_id, Payment.to_user_id == user_id)
    ).first()
    if participant or payer or payment:
        raise HTTPException(409, 'Member has trip transactions')
    for member in members:
        db.delete(member)
    db.commit()
    return {'removed': True}

@router.post('/group/{group_id}/people')
def create_member(group_id: int, person: UserCreate, db: Session = Depends(get_db)):
    if not db.get(Group, group_id):
        raise HTTPException(404, 'Group not found')
    if person.email and db.query(User).filter_by(email=person.email).first():
        raise HTTPException(409, 'Email already registered')
    try:
        user = User(**person.model_dump(), created_by_id=db.info['actor'].id if db.info.get('actor') else None)
        db.add(user)
        db.flush()
        db.add(GroupMember(user_id=user.id, group_id=group_id, role='member'))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Could not register person')
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    if db.info.get('actor'):
        return dict(id=user.id, name=user.name, email=user.email, can_edit=True)
    return user

@router.post("/")
def add_member(
    member: GroupMemberCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member.user_id).first()

    if user is None:
        return {"message": "User not found"}

    
    group = db.query(Group).filter(Group.id == member.group_id).first()

    if group is None:
        return {"message": "Group not found"}

    existing_member = db.query(GroupMember).filter(
        or_(GroupMember.user_id == member.user_id, GroupMember.access_user_id == member.user_id),
        GroupMember.group_id == member.group_id
    ).first()

    if existing_member is not None:
        return {"message": "User is already a member of this group"}

    if member.role not in ["owner", "member"]:
        return {"message": "Invalid role"}

    new_member = GroupMember(
        user_id=member.user_id,
        group_id=member.group_id,
        role=member.role
    )

    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member

@router.get("/group/{group_id}")
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    members = (
        db.query(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )

    return [
        {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": member.role,
            "can_register_expenses": member.can_register_expenses,
            "login_email": db.get(User, member.access_user_id).login_email if member.access_user_id else user.login_email,
            "account_linked": bool(user.auth_subject or member.access_user_id),
            "access_user_id": member.access_user_id,
            "invitation_pending": bool(member.invite_hash),
        }
        for member, user in members
    ]
