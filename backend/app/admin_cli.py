"""Crear admin o employee desde contenedor privado: docker compose exec clients python -m app.admin_cli."""
from datetime import datetime, timezone
from getpass import getpass
from uuid import uuid4
from argon2 import PasswordHasher
from email_validator import validate_email, EmailNotValidError
from pymongo.errors import DuplicateKeyError
from app.common import mongo_db


def main():
    print("Crear cuenta de personal (solo por terminal del contenedor)")
    role = input("Rol [admin/employee] (admin): ").strip().lower() or "admin"
    if role not in {"admin", "employee"}:
        raise SystemExit("Rol inválido")
    nombre = input("Nombre: ").strip()
    email = input("Correo: ").strip().lower()
    password = getpass("Contraseña (12 caracteres mínimo): ")
    if len(nombre) < 3 or len(password) < 12:
        raise SystemExit("Nombre o contraseña demasiado cortos")
    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise SystemExit(str(exc))
    user = {"id": str(uuid4()), "nombre": nombre, "email": email,
            "password_hash": PasswordHasher().hash(password), "role": role,
            "activo": True, "telefono": None, "direcciones": [],
            "creado_en": datetime.now(timezone.utc)}
    try:
        mongo_db().clients.insert_one(user)
    except DuplicateKeyError:
        raise SystemExit("Ya existe un usuario con ese correo")
    print(f"Cuenta {role} creada. Puedes iniciar sesión en /auth/login.")


if __name__ == "__main__":
    main()
