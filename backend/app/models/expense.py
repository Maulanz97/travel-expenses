from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Date, Boolean, JSON
from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    created_by_id = Column(Integer, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(Date, nullable=True)
    voided = Column(Boolean, nullable=False, default=False, server_default='0')
    history = Column(JSON, nullable=False, default=list, server_default='[]')
    custom_shares = Column(JSON, nullable=True)
    payer_contributions = Column(JSON, nullable=True)
    request_id = Column(String(36), nullable=True, unique=True)
    request_fingerprint = Column(String(64), nullable=True)

    payer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = Column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
