import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Language(str, enum.Enum):
    ENGLISH = "en"
    KANNADA = "kn"
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    MALAYALAM = "ml"
    MARATHI = "mr"


class Theme(str, enum.Enum):
    LIGHT = "light"
    DARK = "dark"


class FarmType(str, enum.Enum):
    BROILER = "broiler"
    LAYER = "layer"
    BOTH = "both"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(255))
    farm_name: Mapped[str] = mapped_column(String(255))
    mobile_number: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    profile_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    farm_type: Mapped[FarmType] = mapped_column(Enum(FarmType), default=FarmType.BROILER)
    total_capacity: Mapped[int] = mapped_column(Integer, default=0)
    current_bird_count: Mapped[int] = mapped_column(Integer, default=0)
    preferred_language: Mapped[Language] = mapped_column(Enum(Language), default=Language.ENGLISH)
    preferred_theme: Mapped[Theme] = mapped_column(Enum(Theme), default=Theme.LIGHT)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="user")
    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    login_history: Mapped[list["LoginHistory"]] = relationship(back_populates="user")
    suggested_transactions: Mapped[list["SuggestedTransaction"]] = relationship(back_populates="user")


class LoginHistory(Base):
    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logged_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="login_history")
