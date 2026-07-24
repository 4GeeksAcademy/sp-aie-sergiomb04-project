from __future__ import annotations

from tinydb import Query as TinyQuery
from tinydb import TinyDB
from tinydb.table import Table

USERS_TABLE = "users"
PROFILES_TABLE = "profiles"
PASSWORD_RESET_TOKENS_TABLE = "password_reset_tokens"

_USER_QUERY = TinyQuery()
_PROFILE_QUERY = TinyQuery()
_PASSWORD_RESET_QUERY = TinyQuery()


def get_users_table(db: TinyDB) -> Table:
    return db.table(USERS_TABLE)


def get_profiles_table(db: TinyDB) -> Table:
    return db.table(PROFILES_TABLE)


def get_password_reset_tokens_table(db: TinyDB) -> Table:
    return db.table(PASSWORD_RESET_TOKENS_TABLE)


def get_user_record_by_id(db: TinyDB, user_id: str) -> dict | None:
    return get_users_table(db).get(_USER_QUERY.id == user_id)


def get_user_record_by_email(db: TinyDB, email: str) -> dict | None:
    return get_users_table(db).get(_USER_QUERY.email == email.lower().strip())


def get_profile_record_by_user_id(db: TinyDB, user_id: str) -> dict | None:
    return get_profiles_table(db).get(_PROFILE_QUERY.user_id == user_id)


def email_exists_for_other_user(db: TinyDB, email: str, user_id: str) -> bool:
    normalized_email = email.lower().strip()
    record = get_users_table(db).get(
        (_USER_QUERY.email == normalized_email) & (_USER_QUERY.id != user_id)
    )
    return record is not None


def get_password_reset_token_by_hash(db: TinyDB, token_hash: str) -> dict | None:
    return get_password_reset_tokens_table(db).get(_PASSWORD_RESET_QUERY.token_hash == token_hash)