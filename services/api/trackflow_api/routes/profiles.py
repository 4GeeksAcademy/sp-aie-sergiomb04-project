from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb import Query as TinyQuery

from trackflow_api.auth import get_current_user
from trackflow_api.database import get_db
from trackflow_api.models import ProfileRecord, ProfileUpdate, UserRecord
from trackflow_api.repositories import get_profile_record_by_user_id, get_profiles_table

router = APIRouter(prefix="/profiles", tags=["profiles"])
_PROFILE_QUERY = TinyQuery()


@router.get("/me", response_model=ProfileRecord, status_code=status.HTTP_200_OK)
def get_my_profile(current_user: UserRecord = Depends(get_current_user)) -> ProfileRecord:
    db = get_db()
    profile_record = get_profile_record_by_user_id(db, current_user.id)
    db.close()

    if profile_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return ProfileRecord.model_validate(profile_record)


@router.put("/me", response_model=ProfileRecord, status_code=status.HTTP_200_OK)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: UserRecord = Depends(get_current_user),
) -> ProfileRecord:
    db = get_db()
    profiles_table = get_profiles_table(db)
    existing_profile = get_profile_record_by_user_id(db, current_user.id)

    if existing_profile is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    profiles_table.update(payload.model_dump(mode="json"), _PROFILE_QUERY.user_id == current_user.id)
    updated_profile = get_profile_record_by_user_id(db, current_user.id)
    db.close()

    if updated_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return ProfileRecord.model_validate(updated_profile)