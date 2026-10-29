from functools import lru_cache

from pydantic import AliasChoices, Field
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
    # Heroku supplies HEROKU_SLUG_COMMIT once runtime-dyno-metadata is enabled,
    # which keeps this accurate without a deploy step that can be forgotten.
    git_sha: str = Field(
        default="unknown",
        validation_alias=AliasChoices("EDUBOT_GIT_SHA", "HEROKU_SLUG_COMMIT"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
