"""Genera credenciales locales sin publicarlas en el repositorio ni en el ZIP."""
from pathlib import Path
import secrets
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "secrets"
DEST.mkdir(exist_ok=True)
# Directorio accesible solo por el dueño local; cada archivo se monta de
# forma individual en el contenedor correspondiente.
try:
    DEST.chmod(0o700)
except OSError:
    pass


def put(name: str, content: bytes):
    path = DEST / name
    if path.exists():
        print(f"Conservado: {name}")
        return
    with path.open("xb") as f:
        f.write(content)
    try:
        path.chmod(0o644)
    except OSError:
        pass
    print(f"Generado: {name}")


names = ["mongo-root-password", "mongo-inventory-password", "mongo-orders-password",
         "mongo-clients-password", "mongo-payments-password", "mongo-analytics-password",
         "rabbitmq-password", "service_token"]
for name in names:
    put(name, (secrets.token_urlsafe(48) + "\n").encode())

private_path = DEST / "jwt_private.pem"
public_path = DEST / "jwt_public.pem"
if not private_path.exists() and not public_path.exists():
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    put("jwt_private.pem", key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    put("jwt_public.pem", key.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))
elif private_path.exists() != public_path.exists():
    raise SystemExit("Hay una llave incompleta. Restaura el par JWT original antes de continuar.")

print("\nListo. No compartas el directorio secrets/.")
