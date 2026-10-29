"""The one place this project talks to a language model.

Everything else -- retrieval, solving, grading, choosing the hint level -- is
deterministic Python. The model's only job is to phrase a hint in friendly
English. Keeping that boundary sharp is what makes the tutor testable, and it
is why the whole thing still runs with no API key: `available()` is False and
the caller falls back to a plain template.

Because the job is phrasing and not reasoning, the model is close to a
commodity here, so the provider is a configuration choice rather than an
architectural one. Two are supported, and both are reached through `say()`.
"""

from __future__ import annotations

import os

MAX_TOKENS = 400

# The dyno is talking to someone else's API, not to a student's phone, so this
# is generous. A hint that takes longer than this is not worth waiting for.
TIMEOUT = 30.0

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"

# Ordered cheapest first, because that is the order auto-detection uses when
# more than one key is present -- see `provider()`. The per-provider default
# model is each one's cheapest instruction-following option: phrasing a hint
# does not need a frontier model, and PRD decision 20 records the cost.
PROVIDERS: dict[str, dict[str, str]] = {
    "fireworks": {
        "key": "FIREWORKS_API_KEY",
        # Fireworks rotates its serverless catalogue and retires models, so
        # treat this as a starting point, not a guarantee. `python -m
        # core.models` lists what the configured key can actually serve.
        "model": "accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b",
    },
    "anthropic": {
        "key": "ANTHROPIC_API_KEY",
        "model": "claude-haiku-4-5",
    },
}


def provider() -> str:
    """Which provider to use: the one named, or the cheapest key that is set."""
    named = os.environ.get("EDUBOT_PROVIDER", "").strip().lower()
    if named:
        if named not in PROVIDERS:
            raise ValueError(f"EDUBOT_PROVIDER={named!r} is not one of {sorted(PROVIDERS)}")
        return named
    return next((name for name, spec in PROVIDERS.items() if os.environ.get(spec["key"])), "")


def available() -> bool:
    """True when a key is configured, so callers can degrade gracefully."""
    name = provider()
    return bool(name) and bool(os.environ.get(PROVIDERS[name]["key"]))


def model() -> str:
    """The model id in force, overridable for any provider by EDUBOT_MODEL."""
    override = os.environ.get("EDUBOT_MODEL", "").strip()
    if override:
        return override
    name = provider()
    if not name:
        raise RuntimeError("no provider configured; check available() first")
    return PROVIDERS[name]["model"]


def say(system: str, user: str) -> str:
    """Single, stateless call. The conversation lives in `core.tutor`."""
    name = provider()
    if name == "anthropic":
        return _anthropic(system, user)
    if name == "fireworks":
        return _fireworks(system, user)
    raise RuntimeError("no provider configured; check available() first")


def _anthropic(system: str, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model(),
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _fireworks(system: str, user: str) -> str:
    """Fireworks speaks the OpenAI chat shape, so this is one POST.

    No SDK: the whole surface we use is one endpoint and four fields, and a
    second client library would be 40 MB in the image for no readability.
    """
    # httpx2 is httpx 2.x, which renamed both the distribution and the import.
    # anthropic and starlette both do `import httpx2 as httpx`.
    import httpx2

    chosen = model()
    response = httpx2.post(
        f"{FIREWORKS_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"},
        json={
            "model": chosen,
            "max_tokens": MAX_TOKENS,
            # The OpenAI shape carries the system prompt as a message, where
            # the Messages API takes it as its own argument.
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=TIMEOUT,
    )
    if response.status_code in (400, 404):
        # The usual cause is a retired model id, and the default error text
        # does not say so.
        raise RuntimeError(
            f"Fireworks rejected model {chosen!r} ({response.status_code}). "
            "Run `python -m core.models` to list what this key can serve, "
            "then set EDUBOT_MODEL."
        )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
