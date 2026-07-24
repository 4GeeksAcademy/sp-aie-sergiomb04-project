from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from trackflow_api.auth import create_access_token, get_current_user, verify_password
from trackflow_api.database import get_db
from trackflow_api.models import AuthMeResponse, LoginRequest, TokenResponse, UserRecord
from trackflow_api.repositories import get_profile_record_by_user_id, get_user_record_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest) -> TokenResponse:
    try:
        db = get_db()
        user_record = get_user_record_by_email(db, str(payload.email))
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al iniciar sesion") from error
    db.close()

    if user_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    user = UserRecord.model_validate(user_record)
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=AuthMeResponse, status_code=status.HTTP_200_OK)
def get_auth_me(current_user: UserRecord = Depends(get_current_user)) -> AuthMeResponse:
    try:
        db = get_db()
        profile_record = get_profile_record_by_user_id(db, current_user.id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al obtener perfil") from error
    db.close()

    if profile_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")

    return AuthMeResponse(
        email=current_user.email,
        role=current_user.role,
        profile=profile_record,
    )