from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Language(str, Enum):
    ENGLISH = "en"
    KANNADA = "kn"
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    MALAYALAM = "ml"
    MARATHI = "mr"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class FarmType(str, Enum):
    BROILER = "broiler"
    LAYER = "layer"
    BOTH = "both"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    owner_name: str
    farm_name: str
    mobile_number: str
    state: str
    district: str
    address: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: EmailStr
    owner_name: str
    farm_name: str
    mobile_number: str
    state: str
    district: str
    address: str
    profile_photo: str | None = None
    farm_type: FarmType
    total_capacity: int
    current_bird_count: int
    preferred_language: Language
    preferred_theme: Theme
    voice_enabled: bool
    notifications_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    owner_name: str | None = None
    farm_name: str | None = None
    mobile_number: str | None = None
    state: str | None = None
    district: str | None = None
    address: str | None = None
    farm_type: FarmType | None = None
    total_capacity: int | None = None
    current_bird_count: int | None = None


class SettingsUpdate(BaseModel):
    preferred_language: Language | None = None
    preferred_theme: Theme | None = None
    voice_enabled: bool | None = None
    notifications_enabled: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
