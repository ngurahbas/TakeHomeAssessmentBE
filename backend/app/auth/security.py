import bcrypt
import secrets

from app.auth.roles import ROLE_ADMIN


def hash_password(plaintext: str, *, rounds: int = 12) -> str:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")


def verify_password(plaintext: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


SESSION_KEY_PREFIX = "sess:"


def session_key(token: str) -> str:
    return f"{SESSION_KEY_PREFIX}{token}"


__all__ = [
    "ROLE_ADMIN",
    "hash_password",
    "verify_password",
    "new_token",
    "session_key",
]
