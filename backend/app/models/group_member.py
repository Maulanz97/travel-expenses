from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database import Base


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = Column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String, nullable=False)
    can_register_expenses = Column(Boolean, nullable=False, default=False, server_default='0')
