from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    owner_id: int

class GroupUpdate(BaseModel):
    name: str