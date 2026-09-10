from app.schemas.custom_split import CustomSplit
from decimal import Decimal
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field
from app.schemas.validation import Amount, Description, PositiveId


class ExpenseCreate(CustomSplit):
    request_id: UUID | None = None
    expense_date: date | None = None
    description: Description
    amount: Amount
    payer_id: PositiveId
    group_id: PositiveId
    participants: list[PositiveId] = Field(min_length=1)


class ExpenseUpdate(CustomSplit):
    expense_date: date | None = None
    description: Description
    amount: Amount
    payer_id: PositiveId
    participants: list[PositiveId] = Field(min_length=1)
