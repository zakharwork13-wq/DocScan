import uuid

from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    login: str  # логин или email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: uuid.UUID
    login: str
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    login: str
    email: EmailStr
    password: str
    full_name: str
    role: str = "user"

    @field_validator("login")
    @classmethod
    def login_lowercase(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Пароль должен содержать минимум 12 символов")
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return v
