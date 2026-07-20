from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from trackflow_api.database import get_db
from trackflow_api.models import UserRecord, UserRole
from trackflow_api.repositories import get_user_record_by_id

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "trackflow-dev-secret-key")


def get_access_token_expire_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire_delta = expires_delta or timedelta(minutes=get_access_token_expire_minutes())
    expire_at = datetime.now(timezone.utc) + expire_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire_at,
    }
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserRecord:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or user_id.strip() == "":
            raise _credentials_exception()
    except JWTError as error:
        raise _credentials_exception() from error

    db = get_db()
    record = get_user_record_by_id(db, user_id)
    db.close()

    if record is None:
        raise _credentials_exception()

    user = UserRecord.model_validate(record)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


def require_admin(current_user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user