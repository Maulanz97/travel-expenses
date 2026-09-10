from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib
import json

from app.database import get_db
from app.auth import visible_group_ids
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

def snapshot(expense, db):
    ids = [p.user_id for p in db.query(ExpenseParticipant).filter_by(expense_id=expense.id).all()]
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(ids + [expense.payer_id] + [int(k) for k in (expense.payer_contributions or {})])).all()}
    return dict(description=expense.description, amount=str(Decimal(expense.amount).quantize(Decimal('0.01'))), expense_date=str(expense.expense_date) if expense.expense_date else None,
                payer=names.get(expense.payer_id), payer_contributions=[f'{names.get(int(k), k)}: {v}' for k, v in (expense.payer_contributions or {expense.payer_id: str(expense.amount)}).items()], participants=[names[i] for i in ids], voided=expense.voided, custom_shares=[f'{names[int(k)]}: {v}' for k, v in (expense.custom_shares or {}).items()])

def record_change(expense, before, action, db):
    after = snapshot(expense, db)
    if before != after:
        expense.history = [*(expense.history or []), dict(action=action, at=datetime.now(timezone.utc).isoformat(), before=before, after=after)]

@router.post('/{expense_id}/void')
def void_expense(expense_id: int, db: Session = Depends(get_db)):
    return change_status(expense_id, True, db)

@router.post('/{expense_id}/restore')
def restore_expense(expense_id: int, db: Session = Depends(get_db)):
    return change_status(expense_id, False, db)

def change_status(expense_id, voided, db):
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(404, 'Expense not found')
    before = snapshot(expense, db)
    expense.voided = voided
    record_change(expense, before, 'Anulado' if voided else 'Restaurado', db)
    db.commit()
    db.refresh(expense)
    return expense

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
    request_id = str(expense.request_id) if expense.request_id else None
    original = expense.model_dump(mode='json', exclude={'request_id'})
    # Omit the new optional field for compatibility with pending pre-migration requests.
    if expense.payer_contributions is None:
        original.pop('payer_contributions', None)
    else:
        original['payer_contributions'] = {str(k): format(v, '.2f') for k, v in expense.payer_contributions.items()}
    original['amount'] = format(expense.amount, '.2f')
    if expense.custom_shares is not None:
        original['custom_shares'] = {str(k): format(v, '.2f') for k, v in expense.custom_shares.items()}
    fingerprint = hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()

    def replay():
        existing = db.query(Expense).filter_by(request_id=request_id).first()
        if existing is None:
            return None
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(409, 'Expense request already used with different data')
        return {'id': existing.id, 'replayed': True}

    if request_id:
        previous = replay()
        if previous is not None:
            return previous

    validation_error = validate_expense_participants(
        db=db,
        group_id=expense.group_id,
        payer_id=expense.payer_id,
        participants=expense.participants, payer_contributions=expense.payer_contributions
    )

    if validation_error is not None:
        return {"message": validation_error}

    new_expense = Expense(
        created_by_id=db.info['actor'].id if db.info.get('actor') else None,
        payer_contributions={str(k): str(v) for k, v in expense.payer_contributions.items()} if expense.payer_contributions is not None else None,
        request_id=request_id,
        request_fingerprint=fingerprint if request_id else None,
        custom_shares={str(k): str(v) for k, v in expense.custom_shares.items()} if expense.custom_shares is not None else None,
        description=expense.description,
        expense_date=expense.expense_date,
        amount=expense.amount,
        payer_id=expense.payer_id,
        group_id=expense.group_id
    )

    try:
        db.add(new_expense)
        # Allocate the ID without committing an expense without participants.
        db.flush()
        for user_id in expense.participants:
            db.add(ExpenseParticipant(expense_id=new_expense.id, user_id=user_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        if request_id:
            previous = replay()
            if previous is not None:
                return previous
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "id": new_expense.id,
        "description": new_expense.description,
        "expense_date": new_expense.expense_date,
        "amount": new_expense.amount,
        "payer_id": new_expense.payer_id,
        "group_id": new_expense.group_id,
        "participants": expense.participants
    }


@router.get("/")
def get_expenses(db: Session = Depends(get_db)):
    query = db.query(Expense)
    if db.info.get('actor'):
        query = query.filter(Expense.group_id.in_(visible_group_ids(db, db.info['actor'])))
    expenses = query.all()

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
        participants=expense_data.participants, payer_contributions=expense_data.payer_contributions
    )

    if validation_error is not None:
        return {"message": validation_error}

    if expense.voided:
        raise HTTPException(409, 'Restore the expense before editing')
    before = snapshot(expense, db)
    if "expense_date" in expense_data.model_fields_set:
        expense.expense_date = expense_data.expense_date
    expense.custom_shares = {str(k): str(v) for k, v in expense_data.custom_shares.items()} if expense_data.custom_shares is not None else None
    expense.payer_contributions = {str(k): str(v) for k, v in expense_data.payer_contributions.items()} if expense_data.payer_contributions is not None else None
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

    db.flush()
    record_change(expense, before, 'Editado', db)
    db.commit()
    db.refresh(expense)

    return {
        "id": expense.id,
        "description": expense.description,
        "expense_date": expense.expense_date,
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

    return change_status(expense_id, True, db)

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
        participants=participant_ids, custom_shares=expense.custom_shares
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
        payer_contributions=expense.payer_contributions,
        amount=expense.amount,
        payer_id=expense.payer_id,
        participants=participant_ids, custom_shares=expense.custom_shares
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
