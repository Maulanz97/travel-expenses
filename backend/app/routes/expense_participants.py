from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.expense import Expense
from app.models.expense_participant import ExpenseParticipant
from app.models.group_member import GroupMember
from app.models.user import User
from app.schemas.expense_participant import ExpenseParticipantCreate
from app.services.group_service import get_group_membership

router = APIRouter(
    prefix="/expense-participants",
    tags=["Expense Participants"]
)

@router.post("/")
def add_participant(
    participant: ExpenseParticipantCreate,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == participant.expense_id
    ).first()

    if expense is None:
        return {"message": "Expense not found"}

    if expense.custom_shares is not None:
        return {'message': 'Edit the expense to change custom participants'}

    user = db.query(User).filter(
        User.id == participant.user_id
    ).first()

    if user is None:
        return {"message": "User not found"}

    member = get_group_membership(participant.user_id, expense.group_id, db)

    if member is None:
        return {"message": "User is not a member of this group"}

    existing_participant = db.query(
        ExpenseParticipant
    ).filter(
        ExpenseParticipant.expense_id == participant.expense_id,
        ExpenseParticipant.user_id == participant.user_id
    ).first()

    if existing_participant is not None:
        return {"message": "User is already a participant"}

    new_participant = ExpenseParticipant(
        expense_id=participant.expense_id,
        user_id=participant.user_id
    )

    db.add(new_participant)
    db.commit()
    db.refresh(new_participant)

    return new_participant


@router.get("/expense/{expense_id}")
def get_expense_participants(
    expense_id: int,
    db: Session = Depends(get_db)
):
    participants = (
        db.query(ExpenseParticipant, User)
        .join(
            User,
            ExpenseParticipant.user_id == User.id
        )
        .filter(
            ExpenseParticipant.expense_id == expense_id
        )
        .all()
    )

    return [
        {
            "user_id": user.id,
            "name": user.name,
            "email": user.email
        }
        for participant, user in participants
    ]