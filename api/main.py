from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from api.config import get_settings
from core.tutor import Tutor

app = FastAPI(
    title="EduBot Africa",
    description="AI maths tutor grounded in the Ghanaian JHS (B7-B9) curriculum",
    version="0.1.0",
)

# Students pay for every byte. The page is 7.6 KB of text that compresses to
# about 3 KB, and JSON replies compress well too.
app.add_middleware(GZipMiddleware, minimum_size=500)


PAGE = Path("web/index.html")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    """The whole interface: one file, no build step, no external requests."""
    return HTMLResponse(PAGE.read_text(encoding="utf-8"))


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
    # The API is stateless: the caller owns how far up the Hint Ladder the
    # student is, the same way the Messages API makes the caller own history.
    hint_level: int = Field(default=0, ge=0, le=4)
    student_answer: str | None = None


class Citation(BaseModel):
    heading: str
    grade: int
    url: str
    attribution: str
    score: float


class Reply(BaseModel):
    reply: str
    hint_level: int
    student_was_correct: bool | None
    citations: list[Citation]


@lru_cache
def get_tutor() -> Tutor:
    """Built once per process: the corpus is parsed and vectorised on first use."""
    return Tutor()


@app.post("/chat", response_model=Reply, tags=["tutor"])
def chat(ask: Ask) -> Reply:
    turn = get_tutor().respond(
        ask.question, hint_level=ask.hint_level, student_answer=ask.student_answer
    )
    return Reply(
        reply=turn.reply,
        hint_level=turn.hint_level,
        student_was_correct=turn.student_was_correct,
        citations=[
            Citation(
                heading=c.heading,
                grade=c.grade,
                url=c.url,
                attribution=c.attribution,
                score=c.score,
            )
            for c in turn.citations
        ],
    )
