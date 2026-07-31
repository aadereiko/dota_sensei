from functools import lru_cache
from typing import Annotated, Any

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _blank_to_none(value: Any) -> Any:
    """`FOO=` in a .env file arrives as "", which is not a valid int (or api key).

    Treat an empty or whitespace-only setting as "unset", so the placeholder keys
    in .env.example don't blow up startup.
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


BlankAsNone = BeforeValidator(_blank_to_none)


class Settings(BaseSettings):
    """Runtime configuration. Every field can be set via a DOTA_SENSEI_* env var."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_prefix="DOTA_SENSEI_",
        extra="ignore",
    )

    # --- HTTP ---
    # 8273 is deliberately outside the ranges used by opik (8000/8080/8081/8888)
    # and psy/computational-learning (8321).
    api_host: str = "127.0.0.1"
    api_port: int = 8273
    frontend_origin: str = "http://localhost:5273"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://dota_sensei:dota_sensei@localhost:5473/dota_sensei"
    )
    db_echo: bool = False

    # --- OpenDota ---
    opendota_base_url: str = "https://api.opendota.com/api"
    opendota_api_key: Annotated[str | None, BlankAsNone] = None
    opendota_timeout_seconds: float = 20.0

    # Convenience so the UI can preload without typing an id every time.
    default_account_id: Annotated[int | None, BlankAsNone] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
