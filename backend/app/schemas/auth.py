from pydantic import BaseModel, Field

AUTH_SCHEME = "bearer"


class OtpRequest(BaseModel):
    mobile_number: str = Field(min_length=8, max_length=20)
    device_id: str = Field(min_length=1, max_length=160)


class OtpVerify(OtpRequest):
    code: str = Field(pattern=r"^\d{6}$")


class StaffLogin(BaseModel):
    staff_identifier: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class StaffMfaVerify(BaseModel):
    challenge_token: str = Field(min_length=32, max_length=4096)
    code: str = Field(min_length=6, max_length=32)
    device_id: str = Field(min_length=1, max_length=160)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)
    device_id: str = Field(min_length=1, max_length=160)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = AUTH_SCHEME
    access_expires_in: int
