from decimal import Decimal

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    description: str
    amount: Decimal = Field(gt=0)
    payer_id: int
    group_id: int
    participants: list[int]


class ExpenseUpdate(BaseModel):
    description: str
    amount: Decimal = Field(gt=0)
    payer_id: int
    participants: list[int]