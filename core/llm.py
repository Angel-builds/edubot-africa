"""The one place this project talks to a language model.

Everything else -- retrieval, solving, grading, choosing the hint level -- is
deterministic Python. The model's only job is to phrase a hint in friendly
English. Keeping that boundary sharp is what makes the tutor testable, and it
is why the whole thing still runs with no API key: `available()` is False and
the caller falls back to a plain template.
"""

from __future__ import annotations

import os

# The approved plan picks Haiku as the default tutor model: a pilot of ~5,000
# messages costs about $25, and the work here is phrasing, not reasoning.
MODEL = os.environ.get("EDUBOT_MODEL", "claude-haiku-4-5")
MAX_TOKENS = 400


def available() -> bool:
    """True when a key is configured, so callers can degrade gracefully."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def say(system: str, user: str) -> str:
    """Single, stateless call. The conversation lives in `core.tutor`."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
