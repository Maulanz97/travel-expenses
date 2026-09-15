from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, UniqueConstraint
from app.database import Base


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint('group_id', 'access_user_id', name='uq_trip_access_user'),)

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
    access_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    invite_hash = Column(String(64), nullable=True, unique=True)
    invite_expires = Column(DateTime, nullable=True)
