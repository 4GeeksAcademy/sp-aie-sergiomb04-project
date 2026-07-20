from __future__ import annotations

import argparse
from getpass import getpass

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
        description=(
            "Crea usuarios en TinyDB. Si faltan argumentos, los solicita en modo interactivo."
        )
    )
    parser.add_argument("--email", help="Email del usuario")
    parser.add_argument("--password", help="Contrasena inicial (minimo 8 caracteres)")
    parser.add_argument("--name", help="Nombre del perfil")
    parser.add_argument("--phone", help="Telefono del perfil")
    parser.add_argument("--address", help="Direccion del perfil")
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        help="Rol del usuario",
    )
    parser.add_argument(
        "--is-active",
        dest="is_active",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Estado de activacion de la cuenta (usa --is-active o --no-is-active)",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Si el usuario ya existe, actualiza sus datos.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Si el usuario ya existe, reemplaza su contrasena por la indicada.",
    )
    return parser


def _prompt_text(label: str, *, secret: bool = False) -> str:
    while True:
        value = getpass(f"{label}: ") if secret else input(f"{label}: ")
        value = value.strip()
        if value:
            return value
        print("Valor requerido. Intentalo de nuevo.")


def _parse_bool(raw: str) -> bool | None:
    truthy = {"s", "si", "y", "yes", "true", "1"}
    falsy = {"n", "no", "false", "0"}
    value = raw.strip().lower()
    if value in truthy:
        return True
    if value in falsy:
        return False
    return None


def _prompt_bool(label: str, *, default: bool) -> bool:
    hint = "S/n" if default else "s/N"
    while True:
        raw = input(f"{label} [{hint}]: ").strip()
        if raw == "":
            return default
        parsed = _parse_bool(raw)
        if parsed is not None:
            return parsed
        print("Respuesta invalida. Usa s/si/y/yes o n/no.")


def _prompt_role(default: UserRole | None = None) -> UserRole:
    options = list(UserRole)
    prompt_lines = ["Selecciona un rol:"]
    for index, role in enumerate(options, start=1):
        prompt_lines.append(f"  {index}. {role.value}")

    if default is not None:
        prompt_lines.append(f"Presiona Enter para mantener: {default.value}")

    print("\n".join(prompt_lines))

    while True:
        raw = input("Rol (numero o valor): ").strip().lower()
        if raw == "" and default is not None:
            return default

        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(options):
                return options[selected - 1]

        for role in options:
            if raw == role.value:
                return role

        print("Rol invalido. Elige numero o valor permitido.")


def _get_required(value: str | None, label: str, *, secret: bool = False) -> str:
    if value is not None and value.strip() != "":
        return value.strip()
    return _prompt_text(label, secret=secret)


def _get_role(value: str | None, default: UserRole | None = None) -> UserRole:
    if value is not None:
        return UserRole(value)
    return _prompt_role(default)


def _get_is_active(value: bool | None, *, default: bool) -> bool:
    if value is not None:
        return value
    return _prompt_bool("Cuenta activa", default=default)


def _build_profile_payload(args: argparse.Namespace) -> tuple[str, str, str]:
    name = _get_required(args.name, "Nombre")
    phone = _get_required(args.phone, "Telefono")
    address = _get_required(args.address, "Direccion")
    return name, phone, address


def _build_user_create_payload(args: argparse.Namespace) -> UserCreate:
    name, phone, address = _build_profile_payload(args)
    password = _get_required(args.password, "Contrasena", secret=True)

    return UserCreate.model_validate(
        {
            "email": _get_required(args.email, "Email"),
            "password": password,
            "name": name,
            "phone": phone,
            "address": address,
        }
    )


def main() -> None:
    args = build_parser().parse_args()

    email = _get_required(args.email, "Email")

    db = get_db()
    users_table = get_users_table(db)
    profiles_table = get_profiles_table(db)
    existing_user = get_user_record_by_email(db, email)

    if existing_user is not None:
        user = UserRecord.model_validate(existing_user)

        should_update_existing = args.update_existing
        if not should_update_existing:
            should_update_existing = _prompt_bool(
                "El usuario ya existe. Deseas actualizarlo", default=False
            )

        if not should_update_existing and not args.reset_password:
            db.close()
            raise SystemExit(
                "Operacion cancelada. Usa --update-existing y/o --reset-password para usuarios existentes."
            )

        role = _get_role(args.role, default=user.role)
        is_active = _get_is_active(args.is_active, default=user.is_active)
        name, phone, address = _build_profile_payload(args)

        update_data: dict[str, object] = {
            "role": role.value,
            "is_active": is_active,
        }

        if args.reset_password:
            password = _get_required(args.password, "Contrasena", secret=True)
            update_data["hashed_password"] = get_password_hash(password)

        users_table.update(update_data, TinyQuery().id == user.id)

        profile_data = {
            "name": name,
            "phone": phone,
            "address": address,
        }
        profile_record = profiles_table.get(TinyQuery().user_id == user.id)
        if profile_record is None:
            profiles_table.insert(
                {
                    "id": f"profile-{user.id}",
                    "user_id": user.id,
                    **profile_data,
                }
            )
        else:
            profiles_table.update(profile_data, TinyQuery().user_id == user.id)

        db.close()
        print(f"Usuario actualizado: {user.email} (role={role.value}, is_active={is_active})")
        return

    payload = _build_user_create_payload(args)
    role = _get_role(args.role)
    is_active = _get_is_active(args.is_active, default=True)

    user = user_record_from_create(payload, get_password_hash(payload.password))
    profile = {
        "id": f"profile-{user.id}",
        "user_id": user.id,
        "name": payload.name,
        "phone": payload.phone,
        "address": payload.address,
    }

    user_data = user.model_dump(mode="json")
    user_data["role"] = role.value
    user_data["is_active"] = is_active

    users_table.insert(user_data)
    profiles_table.insert(profile)
    db.close()

    print(
        f"Usuario creado: {payload.email} (role={role.value}, is_active={is_active})"
    )


if __name__ == "__main__":
    main()
