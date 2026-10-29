from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
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


# Heroku terminates TLS at its router, then forwards the request to the dyno
# over plain HTTP, so the scheme the student actually used survives only in
# this header. Trusting a client-supplied header is normally a mistake; here
# the router overwrites it on every request, and the check does nothing
# outside production anyway.
FORWARDED_PROTO = "x-forwarded-proto"

# Thirty days. Long enough that a returning student skips the redirect
# altogether -- one saved round trip on congested mobile data is worth more
# than the header costs to send -- and short enough that moving to a host
# without TLS would not lock anyone out for a year. See PRD decision 12.
HSTS = "max-age=2592000"


# Added after GZipMiddleware, which makes it the outer layer: a redirect is
# decided before the compressor ever sees the response.
@app.middleware("http")
async def require_https(request: Request, call_next):
    """Redirect plain HTTP to HTTPS, and ask the browser not to try HTTP again."""
    if get_settings().environment != "production":
        return await call_next(request)

    if request.headers.get(FORWARDED_PROTO) == "http":
        # 301, not 302: the browser remembers it and stops paying for the
        # round trip. Safe here because the redirect is unconditional.
        return RedirectResponse(request.url.replace(scheme="https"), status_code=301)

    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = HSTS
    return response


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
