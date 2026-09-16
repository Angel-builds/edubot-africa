from fastapi import FastAPI
from pydantic import BaseModel

from api.config import get_settings

app = FastAPI(
    title="EduBot Africa",
    description="AI maths tutor grounded in the Ghanaian JHS (B7-B9) curriculum",
    version="0.1.0",
)


class Health(BaseModel):
    ok: bool
    environment: str
    git_sha: str


@app.get("/health", response_model=Health, tags=["ops"])
def health() -> Health:
    """Liveness probe. Fly.io's health check and the Supabase keepalive both hit this."""
    settings = get_settings()
    return Health(
        ok=True,
        environment=settings.environment,
        git_sha=settings.git_sha,
    )
