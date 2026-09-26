from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from api.config import get_settings
from core.tutor import Tutor

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


class Ask(BaseModel):
    question: str
    # The API is stateless: the client owns how far the student has climbed,
    # the same way the Messages API makes the caller own the conversation.
    level: int = Field(default=0, ge=0, le=4)
    student_answer: str | None = None


class Source(BaseModel):
    heading: str
    grade: int
    url: str
    attribution: str
    score: float


class Reply(BaseModel):
    reply: str
    level: int
    student_was_correct: bool | None
    sources: list[Source]


@lru_cache
def get_tutor() -> Tutor:
    """Built once per process: the corpus is parsed and vectorised on first use."""
    return Tutor()


@app.post("/chat", response_model=Reply, tags=["tutor"])
def chat(ask: Ask) -> Reply:
    turn = get_tutor().respond(
        ask.question, level=ask.level, student_answer=ask.student_answer
    )
    return Reply(
        reply=turn.reply,
        level=turn.level,
        student_was_correct=turn.student_was_correct,
        sources=[
            Source(
                heading=s.heading,
                grade=s.grade,
                url=s.url,
                attribution=s.attribution,
                score=s.score,
            )
            for s in turn.sources
        ],
    )
