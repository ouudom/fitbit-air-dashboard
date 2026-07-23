from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class SetupRequest(Credentials):
    setup_token: str = Field(min_length=1)


class SessionResponse(BaseModel):
    authenticated: bool = True
    user: dict[str, str]
    csrf_token: str | None = None
