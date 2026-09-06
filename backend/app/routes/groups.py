from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant

from app.services.expense_service import (
    calculate_group_balances,
    calculate_settlements
)

router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)

def get_group_or_none(
    group_id: int,
    db: Session
):
    return db.query(Group).filter(
        Group.id == group_id
    ).first()

@router.post("/")
def create_group(group: GroupCreate, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.id == group.owner_id).first()

    if owner is None:
        return {"message": "Owner not found"}

    new_group = Group(
        name=group.name
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    new_member = GroupMember(
        user_id=group.owner_id,
        group_id=new_group.id,
        role="owner"
    )

    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return {
        "id": new_group.id,
        "name": new_group.name,
    }

@router.get("/")
def get_groups(db: Session = Depends(get_db)):
    groups = db.query(Group).all()

    return groups

@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    return group

@router.put("/{group_id}")
def update_group(
    group_id: int,
    group_data: GroupUpdate,
    db: Session = Depends(get_db)
):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    group.name = group_data.name

    db.commit()
    db.refresh(group)

    return group

@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    db.delete(group)
    db.commit()

    return {"message": "Group deleted successfully"}

def get_group_expenses_data(group_id: int, db: Session):
    expenses = db.query(Expense).filter(
        Expense.group_id == group_id
    ).all()

    if not expenses:
        return []

    expense_ids = [expense.id for expense in expenses]

    participants = db.query(ExpenseParticipant).filter(
        ExpenseParticipant.expense_id.in_(expense_ids)
    ).all()

    participants_by_expense = {}

    for participant in participants:
        participants_by_expense.setdefault(
            participant.expense_id, []
        ).append(participant.user_id)

    return [
        {
            "amount": expense.amount,
            "payer_id": expense.payer_id,
            "participants": participants_by_expense.get(
                expense.id, []
            )
        }
        for expense in expenses
    ]

@router.get("/{group_id}/balances")
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db)
):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    expenses_data = get_group_expenses_data(group_id, db)

    balances = calculate_group_balances(
        expenses_data
    )

    user_ids = list(balances.keys())

    users = db.query(User).filter(
        User.id.in_(user_ids)
    ).all()

    users_by_id = {
        user.id: user
        for user in users
    }

    result = []

    for user_id, balance in balances.items():
        user = users_by_id[user_id]

        result.append({
            "user_id": user.id,
            "name": user.name,
            "balance": balance
        })

    return result

@router.get("/{group_id}/settlements")
def get_group_settlements(
    group_id: int,
    db: Session = Depends(get_db)
):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    expenses_data = get_group_expenses_data(group_id, db)

    balances = calculate_group_balances(
        expenses_data
    )

    settlements = calculate_settlements(
        balances
    )

    user_ids = set()

    for settlement in settlements:
        user_ids.add(settlement["from_user"])
        user_ids.add(settlement["to_user"])

    users = db.query(User).filter(
        User.id.in_(user_ids)
    ).all()

    users_by_id = {
        user.id: user
        for user in users
    }

    result = []

    for settlement in settlements:
        from_user = users_by_id[
            settlement["from_user"]
        ]

        to_user = users_by_id[
            settlement["to_user"]
        ]

        result.append({
            "from_user_id": from_user.id,
            "from_user": from_user.name,
            "to_user_id": to_user.id,
            "to_user": to_user.name,
            "amount": settlement["amount"]
        })

    return result

