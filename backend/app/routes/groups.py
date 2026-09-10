from fastapi import APIRouter, Depends
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.auth import visible_group_ids

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant

from app.services.expense_service import (
    calculate_balances,
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
    actor = db.info.get('actor')
    if actor:
        group = group.model_copy(update={'owner_id': actor.id, 'organizer': None})
    owner = db.get(User, group.owner_id) if group.owner_id else None

    if group.owner_id and owner is None:
        return {"message": "Owner not found"}

    new_group = Group(
        name=group.name
    )

    try:
        if group.organizer:
            owner = User(**group.organizer.model_dump())
            db.add(owner)
            db.flush()
        db.add(new_group)
        # Allocate the ID; persist the trip only together with its organizer.
        db.flush()
        db.add(GroupMember(
            user_id=owner.id,
            group_id=new_group.id,
            role="owner"
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": new_group.id,
        "name": new_group.name,
    }

@router.get("/")
def get_groups(db: Session = Depends(get_db)):
    query = db.query(Group, func.count(GroupMember.id)).outerjoin(GroupMember, GroupMember.group_id == Group.id)
    actor = db.info.get('actor')
    if actor:
        query = query.filter(Group.id.in_(visible_group_ids(db, actor)))
    rows = query.group_by(Group.id).all()
    return [{'id': group.id, 'name': group.name, 'member_count': count} for group, count in rows]

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
        Expense.group_id == group_id, Expense.voided == False
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
            "id": expense.id,
            "description": expense.description,
            "expense_date": expense.expense_date,
            "amount": expense.amount,
            "custom_shares": expense.custom_shares,
            "payer_contributions": expense.payer_contributions,
            "payer_id": expense.payer_id,
            "participants": participants_by_expense.get(
                expense.id, []
            )
        }
        for expense in expenses
    ]

def balances_with_payments(group_id, expenses_data, db):
    return {user_id: row['balance'] for user_id, row in balance_breakdowns(group_id, expenses_data, db).items()}


def balance_breakdowns(group_id, expenses_data, db, include_movements=False):
    rows = {}

    def row(user_id):
        result = rows.setdefault(user_id, dict.fromkeys(
            ('expenses_paid', 'expense_share', 'payments_sent', 'payments_received'), Decimal('0.00')
        ))
        if include_movements:
            result.setdefault('movements', {key: [] for key in ('expenses_paid', 'expense_share', 'payments_sent', 'payments_received')})
        return result

    for expense in expenses_data:
        if not expense['participants']:
            continue
        for item in calculate_balances(expense['amount'], expense['payer_id'], expense['participants'], expense.get('custom_shares'), expense.get('payer_contributions')):
            row(item['user_id'])['expenses_paid'] += item['paid']
            row(item['user_id'])['expense_share'] += item['share']
            if include_movements:
                for key, value in (('expenses_paid', item['paid']), ('expense_share', item['share'])):
                    if value or (key == 'expense_share' and item['user_id'] in expense['participants']):
                        row(item['user_id'])['movements'][key].append(dict(id=expense['id'], description=expense['description'], date=expense['expense_date'], amount=value))
    names = dict(db.query(User.id, User.name).all()) if include_movements else {}
    for payment in db.query(Payment).filter_by(group_id=group_id, voided=False).all():
        row(payment.from_user_id)['payments_sent'] += payment.amount
        row(payment.to_user_id)['payments_received'] += payment.amount
        if include_movements:
            row(payment.from_user_id)['movements']['payments_sent'].append(dict(id=payment.id, description=f"Pago a {names.get(payment.to_user_id, 'integrante')}", date=payment.payment_date, amount=payment.amount))
            row(payment.to_user_id)['movements']['payments_received'].append(dict(id=payment.id, description=f"Pago de {names.get(payment.from_user_id, 'integrante')}", date=payment.payment_date, amount=payment.amount))
    for item in rows.values():
        item['balance'] = item['expenses_paid'] - item['expense_share'] + item['payments_sent'] - item['payments_received']
        if include_movements:
            for movements in item['movements'].values():
                movements.sort(key=lambda movement: (str(movement['date'] or ''), movement['id']), reverse=True)
    return rows


@router.get("/{group_id}/balances")
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db)
):
    group = get_group_or_none(group_id, db)

    if group is None:
        return {"message": "Group not found"}

    expenses_data = get_group_expenses_data(group_id, db)

    breakdowns = balance_breakdowns(group_id, expenses_data, db, include_movements=True)
    balances = {user_id: item['balance'] for user_id, item in breakdowns.items()}

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
            "balance": balance,
            "breakdown": {key: value for key, value in breakdowns[user_id].items() if key != 'movements'},
            "movements": breakdowns[user_id]['movements']
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

    balances = balances_with_payments(group_id, expenses_data, db)

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
