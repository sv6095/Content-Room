"""
Authentication Router backed by DynamoDB.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from config import settings
from services.dynamo_repositories import get_users_repo

logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class CurrentUser(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool = True
    preferred_language: Optional[str] = "en"
    created_at: datetime


class UserResponse(CurrentUser):
    pass


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def _to_current_user(item: dict) -> CurrentUser:
    return CurrentUser(
        id=item["user_id"],
        name=item.get("name", "User"),
        email=item["email"],
        is_active=bool(item.get("is_active", True)),
        preferred_language=item.get("preferred_language", "en"),
        created_at=datetime.fromisoformat(item.get("created_at", datetime.utcnow().isoformat())),
    )


def _to_user_response(item: dict) -> UserResponse:
    return UserResponse(**_to_current_user(item).model_dump())


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[CurrentUser]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None
    user = get_users_repo().get_by_id(str(user_id))
    if not user or not user.get("is_active", True):
        return None
    return _to_current_user(user)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise credentials_exception from exc
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    user = get_users_repo().get_by_id(str(user_id))
    if not user:
        raise credentials_exception
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return _to_current_user(user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    users = get_users_repo()
    normalized_name = user_data.name.strip()
    normalized_email = str(user_data.email).strip().lower()
    existing = users.get_by_email(normalized_email)
    if existing:
        # Idempotent registration: if the same user retries with the same
        # credentials, return a fresh token instead of failing.
        existing_hash = existing.get("password_hash", "")
        if existing_hash and verify_password(user_data.password, existing_hash):
            if not existing.get("is_active", True):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
            access_token = create_access_token(data={"sub": existing["user_id"]})
            return TokenResponse(
                access_token=access_token,
                user=_to_user_response(existing),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Please log in.",
        )
    user = users.create_user(
        name=normalized_name,
        email=normalized_email,
        password_hash=hash_password(user_data.password),
    )
    access_token = create_access_token(data={"sub": user["user_id"]})
    return TokenResponse(
        access_token=access_token,
        user=_to_user_response(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_users_repo().get_by_email(form_data.username.lower())
    if not user or not verify_password(form_data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token = create_access_token(data={"sub": user["user_id"]})
    return TokenResponse(
        access_token=access_token,
        user=_to_user_response(user),
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: CurrentUser = Depends(get_current_user)):
    return UserResponse(**current_user.model_dump())


@router.post("/logout", response_model=MessageResponse)
async def logout():
    return MessageResponse(message="Successfully logged out")
