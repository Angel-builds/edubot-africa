"""Keep the test suite offline and unpaid.

`core.tutor.respond` calls the model whenever a key is configured, so a
developer with FIREWORKS_API_KEY or ANTHROPIC_API_KEY exported would otherwise
turn `uv run pytest` into a few dozen real API calls -- billed, slow, and
non-deterministic, which is the opposite of what these tests are for.

Clearing the keys for every test means the tutor tests always exercise the
template fallback. Tests that want a provider set it themselves; this fixture
runs first, so their own setenv still wins.
"""

import pytest

PROVIDER_ENV = (
    "ANTHROPIC_API_KEY",
    "FIREWORKS_API_KEY",
    "EDUBOT_PROVIDER",
    "EDUBOT_MODEL",
)


@pytest.fixture(autouse=True)
def _no_live_model_calls(monkeypatch):
    for name in PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)
