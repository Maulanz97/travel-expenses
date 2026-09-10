from app.schemas.validation import Amount
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentCreate(BaseModel):
    group_id: int = Field(gt=0)
    from_user_id: int = Field(gt=0)
    to_user_id: int = Field(gt=0)
    amount: Amount
    payment_date: date
    request_id: UUID

    @model_validator(mode="after")
    def distinct_people(self):
        if self.from_user_id == self.to_user_id:
            raise ValueError("Choose two different people")
        return self


def same_request(payment, data):
    return all(getattr(payment, key) == getattr(data, key) for key in (
        "group_id", "from_user_id", "to_user_id", "amount", "payment_date"
    ))


@router.post("/")
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    request_id = str(data.request_id)
    existing = db.query(Payment).filter_by(request_id=request_id).first()
    if existing:
        if not same_request(existing, data):
            raise HTTPException(409, "Request already used with different data")
        return existing
    if not db.get(Group, data.group_id):
        raise HTTPException(404, "Group not found")
    member_count = db.query(GroupMember).filter(
        GroupMember.group_id == data.group_id,
        GroupMember.user_id.in_([data.from_user_id, data.to_user_id]),
    ).count()
    if member_count != 2:
        raise HTTPException(422, "Both people must belong to the group")
    payment = Payment(**data.model_dump(exclude={"request_id"}), request_id=request_id)
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Payment).filter_by(request_id=request_id).first()
        if existing and same_request(existing, data):
            return existing
        raise HTTPException(409, "Payment could not be registered")
    db.refresh(payment)
    return payment


@router.get("/group/{group_id}")
def list_payments(group_id: int, db: Session = Depends(get_db)):
    if not db.get(Group, group_id):
        raise HTTPException(404, "Group not found")
    payments = db.query(Payment).filter_by(group_id=group_id).order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    names = dict(db.query(User.id, User.name).all())
    return [{
        "id": payment.id, "from_user_id": payment.from_user_id,
        "to_user_id": payment.to_user_id, "from_user": names.get(payment.from_user_id),
        "to_user": names.get(payment.to_user_id), "amount": payment.amount,
        "payment_date": payment.payment_date, "voided": payment.voided,
    } for payment in payments]


@router.post("/{payment_id}/void")
def void_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    payment.voided = True
    db.commit()
    db.refresh(payment)
    return payment
