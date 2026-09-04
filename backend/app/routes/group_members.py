from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.schemas.group_member import GroupMemberCreate


router = APIRouter(
    prefix="/group-members",
    tags=["Group Members"]
)

@router.post("/")
def add_member(
    member: GroupMemberCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member.user_id).first()

    if user is None:
        return {"message": "User not found"}

    
    group = db.query(Group).filter(Group.id == member.group_id).first()

    if group is None:
        return {"message": "Group not found"}

    existing_member = db.query(GroupMember).filter(
        GroupMember.user_id == member.user_id,
        GroupMember.group_id == member.group_id
    ).first()

    if existing_member is not None:
        return {"message": "User is already a member of this group"}

    if member.role not in ["owner", "member"]:
        return {"message": "Invalid role"}

    new_member = GroupMember(
        user_id=member.user_id,
        group_id=member.group_id,
        role=member.role
    )

    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member

@router.get("/group/{group_id}")
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    members = (
        db.query(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )

    return [
        {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": member.role
        }
        for member, user in members
    ]
