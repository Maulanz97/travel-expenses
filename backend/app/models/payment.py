from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKey, Integer, Numeric, String
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="payment_positive"),
        CheckConstraint("from_user_id != to_user_id", name="payment_distinct_people"),
    )

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(11, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    request_id = Column(String(36), nullable=False, unique=True)
    voided = Column(Boolean, nullable=False, default=False, server_default='0')
