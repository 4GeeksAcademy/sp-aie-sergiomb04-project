from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb import Query as TinyQuery

from trackflow_api.auth import create_access_token, get_current_user, get_password_hash, verify_password
from trackflow_api.database import get_db
from trackflow_api.models import (
    AuthMeResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetTokenRecord,
    ResetPasswordRequest,
    TokenResponse,
    UserRecord,
    password_reset_token_record_from_create,
)
from trackflow_api.password_reset import (
    build_password_reset_expiration,
    create_password_reset_token,
    hash_password_reset_token,
    send_password_reset_email,
)
from trackflow_api.repositories import (
    get_password_reset_token_by_hash,
    get_password_reset_tokens_table,
    get_profile_record_by_user_id,
    get_user_record_by_email,
    get_users_table,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_USER_QUERY = TinyQuery()
_PASSWORD_RESET_QUERY = TinyQuery()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest) -> TokenResponse:
    db = get_db()
    user_record = get_user_record_by_email(db, str(payload.email))
    db.close()

    if user_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = UserRecord.model_validate(user_record)
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=AuthMeResponse, status_code=status.HTTP_200_OK)
def get_auth_me(current_user: UserRecord = Depends(get_current_user)) -> AuthMeResponse:
    db = get_db()
    profile_record = get_profile_record_by_user_id(db, current_user.id)
    db.close()

    if profile_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return AuthMeResponse(
        email=current_user.email,
        role=current_user.role,
        profile=profile_record,
    )


@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    db = get_db()
    user_record = get_user_record_by_email(db, str(payload.email))

    if user_record is not None:
        user = UserRecord.model_validate(user_record)
        reset_token = create_password_reset_token()
        token_hash = hash_password_reset_token(reset_token)
        expires_at = build_password_reset_expiration()

        token_record = password_reset_token_record_from_create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        get_password_reset_tokens_table(db).insert(token_record.model_dump(mode="json"))

        send_password_reset_email(str(user.email), reset_token)

    db.close()

    # Respuesta constante para evitar enumeracion de usuarios.
    return MessageResponse(detail="Si esa direccion esta registrada, recibiras un enlace en breve.")


@router.post("/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordRequest) -> MessageResponse:
    db = get_db()
    token_hash = hash_password_reset_token(payload.token)
    token_record_raw = get_password_reset_token_by_hash(db, token_hash)

    if token_record_raw is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    token_record = PasswordResetTokenRecord.model_validate(token_record_raw)

    if token_record.used_at is not None:
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already used")

    if token_record.expires_at <= datetime.now(timezone.utc):
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    hashed_password = get_password_hash(payload.new_password)
    users_table = get_users_table(db)
    users_table.update({"hashed_password": hashed_password}, _USER_QUERY.id == token_record.user_id)

    get_password_reset_tokens_table(db).update(
        {"used_at": datetime.now(timezone.utc).isoformat()},
        _PASSWORD_RESET_QUERY.id == token_record.id,
    )
    db.close()

    return MessageResponse(detail="Password updated successfully")


@router.post("/change-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
) -> MessageResponse:
    db = get_db()
    user_record = get_user_record_by_email(db, str(current_user.email))

    if user_record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = UserRecord.model_validate(user_record)
    if not verify_password(payload.current_password, user.hashed_password):
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    get_users_table(db).update(
        {"hashed_password": get_password_hash(payload.new_password)},
        _USER_QUERY.id == user.id,
    )
    db.close()

    return MessageResponse(detail="Password changed successfully")