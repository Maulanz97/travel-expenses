from decimal import Decimal
from typing import Annotated
from pydantic import Field, StringConstraints

Amount = Annotated[Decimal, Field(gt=0, le=Decimal('99999999.99'), max_digits=10, decimal_places=2)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TripName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
PositiveId = Annotated[int, Field(gt=0)]
