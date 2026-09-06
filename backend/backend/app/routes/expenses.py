from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.expense import Expense
from app.models.group import Group
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.models.expense_participant import ExpenseParticipant
from app.models.group_member import GroupMember

from app.services.expense_service import (
    calculate_equal_split,
    calculate_balances,
    validate_expense_participants
)

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)

def get_expense_or_none(
    expense_id: int,
    db: Session
):
    return db.query(Expense).filter(
        Expense.id == expense_id
    ).first()

@router.post("/")
def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db)
):
    validation_error = validate_expense_participants(
        db=db,
        group_id=expense.group_id,
        payer_id=expense.payer_id,
        participants=expense.participants
    )

    if validation_error is not None:
        return {"message": validation_error}

    new_expense = Expense(
        description=expense.description,
        amount=expense.amount,
        payer_id=expense.payer_id,
        group_id=expense.group_id
    )

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    for user_id in expense.participants:
        new_participant = ExpenseParticipant(
            expense_id=new_expense.id,
            user_id=user_id
        )

        db.add(new_participant)

    db.commit()

    return {
        "id": new_expense.id,
        "description": new_expense.description,
        "amount": new_expense.amount,
        "payer_id": new_expense.payer_id,
        "group_id": new_expense.group_id,
        "participants": expense.participants
    }


@router.get("/")
def get_expenses(db: Session = Depends(get_db)):
    expenses = db.query(Expense).all()

    return expenses


@router.get("/{expense_id}")
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = get_expense_or_none(
        expense_id=expense_id,
        db=db
    )

    if expense is None:
        return {"message": "Expense not found"}

    return expense


@router.put("/{expense_id}")
def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: Session = Depends(get_db)
):
    expense = get_expense_or_none(
        expense_id=expense_id,
    db=db
)

    if expense is None:
        return {"message": "Expense not found"}

    validation_error = validate_expense_participants(
        db=db,
        group_id=expense.group_id,
        payer_id=expense_data.payer_id,
        participants=expense_data.participants
    )

    if validation_error is not None:
        return {"message": validation_error}

    expense.description = expense_data.description
    expense.amount = expense_data.amount
    expense.payer_id = expense_data.payer_id

    db.query(ExpenseParticipant).filter(
        ExpenseParticipant.expense_id == expense_id
    ).delete()

    for user_id in expense_data.participants:
        new_participant = ExpenseParticipant(
            expense_id=expense_id,
            user_id=user_id
        )

        db.add(new_participant)

    db.commit()
    db.refresh(expense)

    return {
        "id": expense.id,
        "description": expense.description,
        "amount": expense.amount,
        "payer_id": expense.payer_id,
        "group_id": expense.group_id,
        "participants": expense_data.participants
    }


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = get_expense_or_none(
        expense_id=expense_id,
        db=db
    )

    if expense is None:
        return {"message": "Expense not found"}

    db.delete(expense)
    db.commit()

    return {"message": "Expense deleted successfully"}

@router.get("/{expense_id}/split")
def calculate_expense_split(
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = get_expense_or_none(
    expense_id=expense_id,
    db=db
)

    if expense is None:
        return {"message": "Expense not found"}

    participants = db.query(ExpenseParticipant).filter(
        ExpenseParticipant.expense_id == expense_id
    ).all()

    participant_ids = [
        participant.user_id
        for participant in participants
    ]

    result = calculate_equal_split(
        amount=expense.amount,
        payer_id=expense.payer_id,
        participants=participant_ids
    )

    return result

@router.get("/{expense_id}/balances")
def get_expense_balances(
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = get_expense_or_none(
    expense_id=expense_id,
    db=db
)

    if expense is None:
        return {"message": "Expense not found"}

    participants = db.query(ExpenseParticipant).filter(
        ExpenseParticipant.expense_id == expense_id
    ).all()

    participant_ids = [
        participant.user_id
        for participant in participants
    ]

    balances = calculate_balances(
        amount=expense.amount,
        payer_id=expense.payer_id,
        participants=participant_ids
    )

    result = []

    for balance in balances:
        user = db.query(User).filter(
            User.id == balance["user_id"]
        ).first()

        result.append({
            "user_id": user.id,
            "name": user.name,
            "paid": balance["paid"],
            "share": balance["share"],
            "balance": balance["balance"]
        })

    return result