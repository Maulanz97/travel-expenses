from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import visible_users, can_manage_person
from app.models.user import User
from app.schemas.user import UserCreate
from sqlalchemy import or_
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.models.payment import Payment

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = User(
        created_by_id=db.info['actor'].id if db.info.get('actor') else None,
        name=user.name,
        email=user.email
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email already registered')
    db.refresh(new_user)
    if db.info.get('actor'):
        return dict(id=new_user.id, name=new_user.name, email=new_user.email, can_edit=True)
    return new_user

@router.get("/")
def get_users(db: Session = Depends(get_db)):
    users = visible_users(db, db.info['actor']).all() if db.info.get('actor') else db.query(User).all()
    if not db.info.get('actor'):
        if db.info.get('local_development'):
            return [dict(id=user.id, name=user.name, email=user.email, can_edit=True) for user in users]
        return users
    return [dict(id=user.id, name=user.name, email=user.email, can_edit=can_manage_person(db, db.info['actor'], user)) for user in users]

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        return {"message": "User not found"}

    return dict(id=user.id, name=user.name, email=user.email)

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        return {"message": "User not found"}

    user.name = user_data.name
    user.email = user_data.email

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email already registered')
    db.refresh(user)
    if db.info.get('actor'):
        return dict(id=user.id, name=user.name, email=user.email, can_edit=can_manage_person(db, db.info['actor'], user))
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(404, 'User not found')

    if user.auth_subject or user.login_email:
        raise HTTPException(409, 'Person has account access')
    if db.query(GroupMember).filter_by(user_id=user_id).first():
        raise HTTPException(409, 'Person still belongs to trips')
    has_expense = any(
        expense.payer_id == user_id or expense.created_by_id == user_id
        or str(user_id) in (expense.payer_contributions or {})
        or str(user_id) in (expense.custom_shares or {})
        for expense in db.query(Expense)
    )
    has_payment = db.query(Payment).filter(or_(Payment.from_user_id == user_id, Payment.to_user_id == user_id)).first()
    if has_expense or has_payment or db.query(ExpenseParticipant).filter_by(user_id=user_id).first():
        raise HTTPException(409, 'Person has saved transactions')

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Person has saved transactions')

    return {'deleted': True}
