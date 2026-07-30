import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings(database_url=os.environ.get("DATABASE_URL"))
