from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EDUBOT_",
        extra="ignore",
    )

    environment: str = "development"

    # Set by the deploy so a running machine can be traced back to a commit.
    git_sha: str = "unknown"


@lru_cache
def get_settings() -> Settings:
    return Settings()
