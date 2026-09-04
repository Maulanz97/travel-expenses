from pydantic import BaseModel


class GroupMemberCreate(BaseModel):
    user_id: int
    group_id: int
    role: str