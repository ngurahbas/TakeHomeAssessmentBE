import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str | None = Field(default=None)
    valkey_url: str | None = Field(default=None)
    auth_token_ttl_seconds: int = Field(default=86400)
    auth_bcrypt_rounds: int = Field(default=12)
    seed_admin_email: str | None = Field(default=None)
    seed_admin_password: str | None = Field(default=None)
    seed_properties_enabled: bool = Field(default=False)
    seed_properties_path: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL"),
        valkey_url=os.environ.get("VALKEY_URL"),
        auth_token_ttl_seconds=int(
            os.environ.get("AUTH_TOKEN_TTL_SECONDS", "86400")
        ),
        auth_bcrypt_rounds=int(os.environ.get("AUTH_BCRYPT_ROUNDS", "12")),
        seed_admin_email=os.environ.get("SEED_ADMIN_EMAIL"),
        seed_admin_password=os.environ.get("SEED_ADMIN_PASSWORD"),
        seed_properties_enabled=os.environ.get("SEED_PROPERTIES", "0") == "1",
        seed_properties_path=os.environ.get("SEED_PROPERTIES_PATH") or None,
    )
