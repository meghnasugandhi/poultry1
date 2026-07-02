import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import OperationalError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import LoginHistory, User
from app.schemas.auth import (
    PasswordChange,
    SettingsUpdate,
    Token,
    UserLogin,
    UserProfile,
    UserProfileUpdate,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def record_login_history(request: Request, user: User, db: AsyncSession) -> None:
    login_entry = LoginHistory(
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        device=request.headers.get("user-agent"),
    )
    db.add(login_entry)
    try:
        await db.commit()
    except OperationalError as exc:
        await db.rollback()
        if "database is locked" not in str(exc).lower():
            raise


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        owner_name=data.owner_name,
        farm_name=data.farm_name,
        mobile_number=data.mobile_number,
        state=data.state,
        district=data.district,
        address=data.address,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    await record_login_history(request, user, db)
    return Token(access_token=token)


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    await record_login_history(request, user, db)
    return Token(access_token=token)


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.put("/settings", response_model=UserProfile)
async def update_settings(
    data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(data.new_password)
    return {"message": "Password updated successfully"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.get("/login-history")
async def get_login_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginHistory)
        .where(LoginHistory.user_id == current_user.id)
        .order_by(LoginHistory.logged_in_at.desc())
        .limit(20)
    )
    history = result.scalars().all()
    return [
        {
            "id": h.id,
            "ip_address": h.ip_address,
            "device": h.device,
            "logged_in_at": h.logged_in_at,
        }
        for h in history
    ]


@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import os

    os.makedirs(os.path.join(settings.UPLOAD_DIR, "profiles"), exist_ok=True)
    ext = os.path.splitext(file.filename or "photo")[1] or ".jpg"
    path = os.path.join(settings.UPLOAD_DIR, "profiles", f"{current_user.id}_{uuid.uuid4().hex}{ext}")
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    current_user.profile_photo = path
    await db.flush()
    await db.refresh(current_user)
    return {"profile_photo": path, "message": "Photo updated"}
