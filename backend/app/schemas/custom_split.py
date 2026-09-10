from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, Field, model_validator
from app.schemas.validation import Amount, PositiveId

Share = Annotated[Decimal, Field(ge=0, le=Decimal('99999999.99'), max_digits=10, decimal_places=2)]

class CustomSplit(BaseModel):
    payer_contributions: dict[PositiveId, Amount] | None = None
    custom_shares: dict[int, Share] | None = None

    @model_validator(mode='after')
    def validate_split(self):
        if self.payer_contributions is not None:
            if self.payer_id not in self.payer_contributions:
                raise ValueError('Primary payer must have a contribution')
            if sum(self.payer_contributions.values()) != self.amount:
                raise ValueError('Payer contributions must equal total')
        if len(self.participants) != len(set(self.participants)):
            raise ValueError('Duplicate participants are not allowed')
        if self.custom_shares is not None:
            if set(self.custom_shares) != set(self.participants):
                raise ValueError('Custom shares must match participants')
            if sum(self.custom_shares.values()) != self.amount:
                raise ValueError('Custom shares must equal total')
        return self
