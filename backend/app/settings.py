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

    llm_base_url: str = Field(default="http://localhost:1234/v1")
    llm_api_key: str = Field(default="not-needed")
    llm_model: str = Field(default="local-model")
    llm_timeout_seconds: float = Field(default=60.0)
    llm_max_history_messages: int = Field(default=40)
    llm_max_input_chars: int = Field(default=4000)
    llm_system_prompt: str = Field(
        default=(
            "You are a helpful real-estate assistant. Be concise, factual, "
            "and friendly. If you do not know the answer, say so. "
            "You have access to the `SayNiceThing` tool \u2014 when the user "
            "expresses sadness or says \"I am sad\", use it to cheer them up. "
            "When you use SayNiceThing, output exactly what the tool "
            "returns without adding your own words."
        )
    )


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
        llm_base_url=os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1"),
        llm_api_key=os.environ.get("LLM_API_KEY", "not-needed"),
        llm_model=os.environ.get("LLM_MODEL", "local-model"),
        llm_timeout_seconds=float(
            os.environ.get("LLM_TIMEOUT_SECONDS", "60")
        ),
        llm_max_history_messages=int(
            os.environ.get("LLM_MAX_HISTORY_MESSAGES", "40")
        ),
        llm_max_input_chars=int(
            os.environ.get("LLM_MAX_INPUT_CHARS", "4000")
        ),
        llm_system_prompt=os.environ.get(
            "LLM_SYSTEM_PROMPT",
            (
                "You are a helpful real-estate assistant. Be concise, factual, "
                "and friendly. If you do not know the answer, say so. "
                "You have access to the `SayNiceThing` tool \u2014 when the user "
                "expresses sadness or says \"I am sad\", use it to cheer them up. "
                "When you use SayNiceThing, output exactly what the tool "
                "returns without adding your own words."
            ),
        ),
    )
