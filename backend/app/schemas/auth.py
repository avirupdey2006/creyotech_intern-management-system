import uuid
from datetime import datetime
import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole

# Permit special-use and local domains (e.g. .test, .local) for testing and intranet environments
email_validator.SPECIAL_USE_DOMAIN_NAMES.clear()


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class AuthStatusResponse(BaseModel):
    message: str
    user: UserResponse