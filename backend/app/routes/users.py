from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import visible_users, can_manage_person
from app.models.user import User
from app.schemas.user import UserCreate

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
        return {"message": "User not found"}

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email already registered')

    return {"message": "User deleted successfully"}
