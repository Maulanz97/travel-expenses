from sqlalchemy import Column, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    auth_subject = Column(String(36), unique=True, nullable=True)
    login_email = Column(String(320), unique=True, nullable=True)
    created_by_id = Column(Integer, nullable=True)
    email = Column(String, unique=True, nullable=True, index=True)
