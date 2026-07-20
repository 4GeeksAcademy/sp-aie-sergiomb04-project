from __future__ import annotations

import argparse

from tinydb import Query as TinyQuery

from trackflow_api.auth import get_password_hash
from trackflow_api.database import get_db
from trackflow_api.models import UserCreate, UserRecord, UserRole, user_record_from_create
from trackflow_api.repositories import (
    get_profiles_table,
    get_user_record_by_email,
    get_users_table,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crea un usuario administrador o promociona uno existente en TinyDB."
    )
    parser.add_argument("--email", required=True, help="Email del administrador")
    parser.add_argument("--password", required=True, help="Contraseña inicial")
    parser.add_argument("--name", required=True, help="Nombre del perfil")
    parser.add_argument("--phone", required=True, help="Telefono del perfil")
    parser.add_argument("--address", required=True, help="Direccion del perfil")
    parser.add_argument(
        "--promote-existing",
        action="store_true",
        help="Si el usuario ya existe, lo actualiza a admin y reactiva la cuenta.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Si el usuario ya existe, reemplaza su contraseña por la indicada.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = UserCreate.model_validate(
        {
            "email": args.email,
            "password": args.password,
            "name": args.name,
            "phone": args.phone,
            "address": args.address,
        }
    )

    db = get_db()
    users_table = get_users_table(db)
    profiles_table = get_profiles_table(db)
    existing_user = get_user_record_by_email(db, str(payload.email))

    if existing_user is not None:
      if not args.promote_existing and not args.reset_password:
          db.close()
          raise SystemExit(
              "El usuario ya existe. Usa --promote-existing para convertirlo en admin o "
              "--reset-password para cambiar su contraseña."
          )

      user = UserRecord.model_validate(existing_user)
      update_data: dict[str, object] = {
          "role": UserRole.ADMIN.value,
          "is_active": True,
      }

      if args.reset_password:
          update_data["hashed_password"] = get_password_hash(payload.password)

      users_table.update(update_data, TinyQuery().id == user.id)

      profile_record = profiles_table.get(TinyQuery().user_id == user.id)
      if profile_record is None:
          profiles_table.insert(
              {
                  "id": f"profile-{user.id}",
                  "user_id": user.id,
                  "name": payload.name,
                  "phone": payload.phone,
                  "address": payload.address,
              }
          )

      db.close()
      print(f"Admin actualizado: {user.email}")
      return

    user = user_record_from_create(payload, get_password_hash(payload.password))
    profile = {
        "id": f"profile-{user.id}",
        "user_id": user.id,
        "name": payload.name,
        "phone": payload.phone,
        "address": payload.address,
    }

    user_data = user.model_dump(mode="json")
    user_data["role"] = UserRole.ADMIN.value

    users_table.insert(user_data)
    profiles_table.insert(profile)
    db.close()

    print(f"Admin creado: {payload.email}")


if __name__ == "__main__":
    main()