from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb import Query as TinyQuery

from trackflow_api.auth import get_current_user, get_password_hash, require_admin
from trackflow_api.database import get_db
from trackflow_api.models import (
    ProfileRecord,
    UserCreate,
    UserPublic,
    UserRecord,
    UserRole,
    UserUpdate,
    profile_record_from_user_create,
    user_public_from_record,
    user_record_from_create,
)
from trackflow_api.repositories import (
    email_exists_for_other_user,
    get_profile_record_by_user_id,
    get_profiles_table,
    get_user_record_by_email,
    get_user_record_by_id,
    get_users_table,
)

router = APIRouter(prefix="/users", tags=["users"])
_USER_QUERY = TinyQuery()
_PROFILE_QUERY = TinyQuery()


def _ensure_self_or_admin(current_user: UserRecord, target_user_id: str) -> None:
    if current_user.role != UserRole.ADMIN and current_user.id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> UserPublic:
    db = get_db()
    users_table = get_users_table(db)
    profiles_table = get_profiles_table(db)

    existing_user = get_user_record_by_email(db, str(payload.email))
    if existing_user is not None:
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = user_record_from_create(payload, get_password_hash(payload.password))
    profile = profile_record_from_user_create(user.id, payload)

    users_table.insert(user.model_dump(mode="json"))
    profiles_table.insert(profile.model_dump(mode="json"))
    db.close()

    return user_public_from_record(user)


@router.get("", response_model=list[UserPublic], status_code=status.HTTP_200_OK)
def list_users(_: UserRecord = Depends(require_admin)) -> list[UserPublic]:
    db = get_db()
    records = get_users_table(db).all()
    db.close()
    return [user_public_from_record(UserRecord.model_validate(record)) for record in records]


@router.get("/{user_id}", response_model=UserPublic, status_code=status.HTTP_200_OK)
def get_user(user_id: str, current_user: UserRecord = Depends(get_current_user)) -> UserPublic:
    _ensure_self_or_admin(current_user, user_id)

    db = get_db()
    record = get_user_record_by_id(db, user_id)
    db.close()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_public_from_record(UserRecord.model_validate(record))


@router.put("/{user_id}", response_model=UserPublic, status_code=status.HTTP_200_OK)
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: UserRecord = Depends(get_current_user),
) -> UserPublic:
    _ensure_self_or_admin(current_user, user_id)

    if payload.role is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change roles")

    if payload.is_active is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change activation")

    db = get_db()
    users_table = get_users_table(db)
    record = get_user_record_by_id(db, user_id)

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = payload.model_dump(exclude_none=True)
    if "email" in update_data and email_exists_for_other_user(db, str(update_data["email"]), user_id):
        db.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    if "role" in update_data:
        update_data["role"] = update_data["role"].value

    users_table.update(update_data, _USER_QUERY.id == user_id)
    updated_record = get_user_record_by_id(db, user_id)
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_public_from_record(UserRecord.model_validate(updated_record))


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: str, current_user: UserRecord = Depends(get_current_user)) -> dict[str, str]:
    _ensure_self_or_admin(current_user, user_id)

    db = get_db()
    user_record = get_user_record_by_id(db, user_id)
    if user_record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    get_users_table(db).remove(_USER_QUERY.id == user_id)
    get_profiles_table(db).remove(_PROFILE_QUERY.user_id == user_id)
    db.close()
    return {"detail": "User deleted"}