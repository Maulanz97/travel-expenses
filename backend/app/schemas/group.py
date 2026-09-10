from app.schemas.validation import TripName
from pydantic import BaseModel, Field, model_validator
from app.schemas.user import UserCreate


class GroupCreate(BaseModel):
    name: TripName
    owner_id: int | None = Field(default=None, gt=0)
    organizer: UserCreate | None = None

    @model_validator(mode='after')
    def one_organizer(self):
        if (self.owner_id is None) == (self.organizer is None):
            raise ValueError('Choose an existing organizer or create one')
        return self

class GroupUpdate(BaseModel):
    name: TripName
