from pydantic import BaseModel


class ExpenseParticipantCreate(BaseModel):
    expense_id: int
    user_id: int