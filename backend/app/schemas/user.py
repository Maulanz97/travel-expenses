from app.schemas.validation import PersonName
import re
from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    name: PersonName
    email: str | None = None

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('email', mode='before')
    @classmethod
    def optional_email(cls, value):
        if value is None or not str(value).strip():
            return None
        value = str(value).strip()
        if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Invalid email')
        local, domain = value.split('@')
        if not local or not domain or '.' not in domain:
            raise ValueError('Invalid email')
        return value
